import {
  createCipheriv,
  createDecipheriv,
  hkdfSync,
  randomBytes,
} from "node:crypto";
import type { IModels } from "@/foundation/models";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { ISendGrid } from "@/foundation/sendgrid";
import type { AuthMail, AuthMailKind } from "../data/auth-mail-model";
import { consumeMailDelivery } from "../operations/auth-mail-limits";
import { issueSignInRecoveryProof } from "../operations/sign-in-recovery-proof";
import { validateAuthReturnPath } from "../utils/auth-return-path";
import { prefixedNanoidBase58 } from "@/shared/nanoid-base58";
import { ServiceUnavailableError } from "@/shared/errors";
import { TTL } from "@/shared/cache";
import { logger } from "@/shared/logger";
import {
  renderPasswordResetHtml,
  renderPasswordResetText,
} from "@/shared/email-templates";

const mailLogger = logger.child({ module: "auth-mail-service" });
type Payload = {
  email: string;
  returnTo?: string;
  admitted?: boolean;
  prepared?: {
    userId: string;
    token?: string;
    resetExpiresAt?: number;
    code?: string;
  };
};

export interface IAuthMailService {
  enqueue(
    email: string,
    kind: AuthMailKind,
    returnTo?: string,
  ): Promise<string>;
  processBatch(): Promise<void>;
}

export class AuthMailService implements IAuthMailService {
  private processing = false;

  constructor(
    private readonly models: Pick<IModels, "user" | "emailToken" | "authMail">,
    private readonly db: DbExecutor,
    private readonly sendgrid: ISendGrid,
    private readonly secret: string,
    private readonly dashboardUrl: string,
  ) {}

  public enqueue = async (
    email: string,
    kind: AuthMailKind,
    returnTo?: string,
  ): Promise<string> => {
    const id = prefixedNanoidBase58("aem_");
    const payload = this.encrypt(id, kind, {
      email: email.trim().toLowerCase(),
      returnTo: validateAuthReturnPath(returnTo),
    });
    try {
      // No account lookup, challenge creation or provider work on this path.
      await this.models.authMail.enqueue(this.db, {
        id,
        kind,
        payload,
        expiresAt: new Date(Date.now() + TTL.MIN_5),
      });
    } catch {
      throw new ServiceUnavailableError("Authentication mail", 5);
    }
    return id;
  };

  public async processBatch(): Promise<void> {
    if (this.processing) return;
    this.processing = true;
    try {
      await this.models.authMail.cleanup(this.db);
      for (let count = 0; count < 5; count++) {
        const mail = await this.models.authMail.claim(this.db);
        if (!mail) break;
        try {
          await this.deliver(mail);
        } catch {
          // Neither database errors nor provider exceptions are safe to log:
          // they may contain recipients, request bodies and secret links.
          mailLogger.warn("Authentication mail delivery deferred");
          await this.models.authMail.retry(this.db, mail);
        }
      }
    } catch {
      mailLogger.error("Authentication mail worker unavailable");
    } finally {
      this.processing = false;
    }
  }

  private async deliver(mail: AuthMail): Promise<void> {
    if (mail.expiresAt.getTime() <= Date.now()) {
      await this.models.authMail.complete(this.db, mail);
      return;
    }
    const payload = this.decrypt(mail);
    payload.returnTo = validateAuthReturnPath(payload.returnTo);
    if (!payload.admitted) {
      if (!(await consumeMailDelivery(payload.email))) {
        await this.models.authMail.complete(this.db, mail);
        return;
      }
      payload.admitted = true;
      if (!(await this.save(mail, payload))) return;
    }
    if (!payload.prepared) {
      const user = await this.models.user.getByMail(this.db, payload.email);
      if (!user) {
        await this.models.authMail.complete(this.db, mail);
        return;
      }
      if (mail.kind === "reset") {
        payload.prepared = {
          userId: user.id,
          token: randomBytes(32).toString("hex"),
          resetExpiresAt: Date.now() + TTL.MIN_5,
        };
      } else {
        payload.prepared = { userId: user.id };
      }
    }
    const prepared = payload.prepared;
    // Older queued jobs may predate the persisted reset expiry. Set it once,
    // before issuing anything, so retries cannot extend the reset lifetime.
    if (mail.kind === "reset" && prepared.resetExpiresAt === undefined)
      prepared.resetExpiresAt = Date.now() + TTL.MIN_5;
    // Commit the stable prepared contents before any delivery. A crash after
    // acceptance may resend this same mail, never rotate its code or token.
    if (!(await this.save(mail, payload))) return;
    const proof = await issueSignInRecoveryProof(
      payload.email,
      prepared.userId,
      mail.id,
      this.secret,
    );
    if (proof && !prepared.code) prepared.code = proof.code;
    const signInRecovery =
      proof && proof.code === prepared.code
        ? {
            link: this.recoveryLink(proof.challengeId, payload.returnTo),
            code: proof.code,
          }
        : undefined;
    const dashboard = this.dashboardUrl.replace(/\/$/, "");
    if (mail.kind === "reset") {
      const token = await this.models.emailToken.issueToken(
        prepared.userId,
        prepared.token!,
        new Date(prepared.resetExpiresAt!),
      );
      if (!token) {
        await this.models.authMail.complete(this.db, mail);
        return;
      }
      const resetLink = `${dashboard}/auth/reset-password/?token=${encodeURIComponent(token.token)}`;
      if (!(await this.save(mail, payload))) return;
      await this.sendgrid.sendMail({
        to: payload.email,
        subject: "Reset your Password",
        html: renderPasswordResetHtml({ resetLink, signInRecovery }),
        text: renderPasswordResetText({ resetLink, signInRecovery }),
      });
    } else {
      if (!signInRecovery) {
        await this.models.authMail.complete(this.db, mail);
        return;
      }
      const { link, code } = signInRecovery;
      const htmlLink = link.replace(/&/g, "&amp;");
      if (!(await this.save(mail, payload))) return;
      await this.sendgrid.sendMail({
        to: payload.email,
        subject: "Beancount.io sign-in recovery code",
        text: `Your Beancount.io sign-in recovery code is ${code}. Open ${link} and enter your email, password and this code. Your correct password is still required. If you did not request this code, ignore this email.`,
        html: `<p>Your Beancount.io sign-in recovery code is <strong>${code}</strong>.</p><p><a href="${htmlLink}">Continue signing in</a> with your email, password and this code. Your correct password is still required.</p><p>If you did not request this code, ignore this email.</p>`,
      });
    }
    await this.models.authMail.complete(this.db, mail);
  }

  private recoveryLink(challengeId: string, returnTo?: string): string {
    const search = new URLSearchParams({ recovery: challengeId });
    if (returnTo) search.set("next", returnTo);
    return `${this.dashboardUrl.replace(/\/$/, "")}/auth/login/?${search.toString()}`;
  }

  private save(mail: AuthMail, payload: Payload): Promise<boolean> {
    return this.models.authMail.savePayload(
      this.db,
      mail,
      this.encrypt(mail.id, mail.kind, payload),
    );
  }

  private key(): Buffer {
    if (!this.secret)
      throw new ServiceUnavailableError("Authentication mail", 5);
    return Buffer.from(
      hkdfSync("sha256", this.secret, "", "beancount/auth-mail/v1", 32),
    );
  }

  private encrypt(id: string, kind: AuthMailKind, payload: Payload): string {
    const iv = randomBytes(12);
    const cipher = createCipheriv("aes-256-gcm", this.key(), iv);
    cipher.setAAD(Buffer.from(`${id}:${kind}:v1`));
    const data = Buffer.concat([
      cipher.update(JSON.stringify(payload), "utf8"),
      cipher.final(),
    ]);
    return [
      "v1",
      iv.toString("base64"),
      cipher.getAuthTag().toString("base64"),
      data.toString("base64"),
    ].join(".");
  }

  private decrypt(mail: AuthMail): Payload {
    const [version, iv, tag, data] = mail.payload.split(".");
    if (version !== "v1" || !iv || !tag || !data)
      throw new Error("Invalid authentication mail payload");
    const decipher = createDecipheriv(
      "aes-256-gcm",
      this.key(),
      Buffer.from(iv, "base64"),
    );
    decipher.setAAD(Buffer.from(`${mail.id}:${mail.kind}:v1`));
    decipher.setAuthTag(Buffer.from(tag, "base64"));
    return JSON.parse(
      Buffer.concat([
        decipher.update(Buffer.from(data, "base64")),
        decipher.final(),
      ]).toString("utf8"),
    ) as Payload;
  }
}
