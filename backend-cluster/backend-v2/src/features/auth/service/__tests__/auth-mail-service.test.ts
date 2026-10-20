import { AuthMailService } from "../auth-mail-service";
import type { AuthMail } from "../../data/auth-mail-model";
import { consumeMailDelivery } from "../../operations/auth-mail-limits";
import { issueSignInRecoveryProof } from "../../operations/sign-in-recovery-proof";
import { ServiceUnavailableError } from "@/shared/errors";
import { logger } from "@/shared/logger";
import { createCipheriv, hkdfSync, randomBytes } from "node:crypto";
import { BadUserInputError } from "@/shared/errors";

jest.mock("../../operations/auth-mail-limits", () => ({
  consumeMailDelivery: jest.fn(),
}));
jest.mock("../../operations/sign-in-recovery-proof", () => ({
  issueSignInRecoveryProof: jest.fn(),
}));
jest.mock("@/shared/logger", () => {
  const logs = { warn: jest.fn(), error: jest.fn() };
  return { logger: { child: () => logs } };
});

function fixture(secret = "synthetic-mail-test-secret") {
  const rows = new Map<string, AuthMail>();
  let lease = 0;
  const db = {};
  const owns = (mail: AuthMail) =>
    rows.get(mail.id)?.leaseToken === mail.leaseToken &&
    mail.leaseUntil!.getTime() > Date.now();
  const authMail = {
    enqueue: jest.fn(
      async (
        _db: unknown,
        input: Pick<AuthMail, "id" | "kind" | "payload" | "expiresAt">,
      ) => {
        rows.set(input.id, {
          ...input,
          attempts: 0,
          availableAt: new Date(),
          leaseToken: null,
          leaseUntil: null,
          createdAt: new Date(),
        });
      },
    ),
    claim: jest.fn(async () => {
      const mail = [...rows.values()].find(
        (row) =>
          row.availableAt.getTime() <= Date.now() &&
          (!row.leaseUntil || row.leaseUntil.getTime() <= Date.now()) &&
          row.attempts < 5,
      );
      if (!mail) return null;
      mail.attempts++;
      mail.leaseToken = `lease-${++lease}`;
      mail.leaseUntil = new Date(Date.now() + 60_000);
      return { ...mail };
    }),
    savePayload: jest.fn(
      async (_db: unknown, mail: AuthMail, payload: string) => {
        if (!owns(mail)) return false;
        rows.get(mail.id)!.payload = payload;
        return true;
      },
    ),
    complete: jest.fn(async (_db: unknown, mail: AuthMail) => {
      if (owns(mail)) rows.delete(mail.id);
    }),
    retry: jest.fn(async (_db: unknown, mail: AuthMail) => {
      if (!owns(mail)) return;
      if (mail.attempts >= 5) rows.delete(mail.id);
      else
        Object.assign(rows.get(mail.id)!, {
          leaseToken: null,
          leaseUntil: null,
          availableAt: new Date(Date.now() + 5000),
        });
    }),
    cleanup: jest.fn(async () => {
      for (const [id, row] of rows)
        if (row.expiresAt.getTime() <= Date.now()) rows.delete(id);
    }),
  };
  const user = {
    getByMail: jest.fn(async () => ({
      id: "user_mail",
      email: "person@example.com",
    })),
  };
  const emailToken = {
    issueToken: jest.fn(
      async (userId: string, token: string, expires: Date) => ({
        userId,
        token,
        expireAt: expires.toISOString(),
      }),
    ),
    regenerateToken: jest.fn(),
  };
  const sendgrid = {
    sendMail: jest.fn(
      async (_mail: { to: string; text?: string; html?: string }) => undefined,
    ),
  };
  const service = () =>
    new AuthMailService(
      { authMail, user, emailToken } as never,
      db as never,
      sendgrid as never,
      secret,
      "https://example.com",
    );
  return {
    rows,
    authMail,
    user,
    emailToken,
    sendgrid,
    service,
    retryNow: () => {
      for (const row of rows.values()) row.availableAt = new Date(0);
    },
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(consumeMailDelivery).mockResolvedValue(true);
  jest.mocked(issueSignInRecoveryProof).mockResolvedValue({
    code: "123456",
    challengeId: "rcv_private-challenge",
  });
});

it("enqueues opaque IDs and encrypted recipient data identically before any account lookup", async () => {
  const f = fixture();
  const service = f.service();
  const known = await service.enqueue(" PERSON@example.com ", "reset");
  const unknown = await service.enqueue("unknown@example.com", "reset");
  expect(known).toMatch(/^aem_/);
  expect(unknown).toMatch(/^aem_/);
  expect(known).not.toBe(unknown);
  expect(f.user.getByMail).not.toHaveBeenCalled();
  expect(f.sendgrid.sendMail).not.toHaveBeenCalled();
  for (const row of f.rows.values()) {
    expect(row.payload).toMatch(/^v1\./);
    expect(row.payload).not.toContain("example.com");
    expect(row.expiresAt.getTime() - Date.now()).toBeLessThanOrEqual(300_000);
  }
});

it("rejects missing secrets and persistence outages uniformly without account lookup", async () => {
  const missing = fixture("");
  await expect(
    missing.service().enqueue("person@example.com", "reset"),
  ).rejects.toBeInstanceOf(ServiceUnavailableError);
  expect(missing.authMail.enqueue).not.toHaveBeenCalled();
  const down = fixture();
  down.authMail.enqueue.mockRejectedValue(new Error("database detail"));
  for (const email of ["person@example.com", "unknown@example.com"]) {
    await expect(down.service().enqueue(email, "reset")).rejects.toBeInstanceOf(
      ServiceUnavailableError,
    );
  }
  expect(down.user.getByMail).not.toHaveBeenCalled();
});

it("suppresses delivery before lookup/token creation and preserves existing valid tokens", async () => {
  const f = fixture();
  jest.mocked(consumeMailDelivery).mockResolvedValue(false);
  await f.service().enqueue("person@example.com", "reset");
  await f.service().processBatch();
  expect(f.rows.size).toBe(0);
  expect(f.user.getByMail).not.toHaveBeenCalled();
  expect(f.emailToken.issueToken).not.toHaveBeenCalled();
  expect(f.emailToken.regenerateToken).not.toHaveBeenCalled();
  expect(f.sendgrid.sendMail).not.toHaveBeenCalled();
});

it("retries stable prepared mail after a process restart without rotating its token or spending delivery quota again", async () => {
  const f = fixture();
  const id = await f.service().enqueue("person@example.com", "reset");
  f.sendgrid.sendMail.mockRejectedValueOnce(
    new Error("recipient=person@example.com provider payload secret"),
  );
  await f.service().processBatch();
  expect(f.rows.has(id)).toBe(true);
  const first = f.sendgrid.sendMail.mock.calls[0][0];
  const token = f.emailToken.issueToken.mock.calls[0][1];
  expect(f.rows.get(id)!.payload).not.toContain(token);
  expect(f.rows.get(id)!.payload).not.toContain("person@example.com");
  f.retryNow();

  await f.service().processBatch();

  expect(f.sendgrid.sendMail.mock.calls[1][0]).toEqual(first);
  expect(f.emailToken.issueToken.mock.calls[1][1]).toBe(token);
  expect(f.emailToken.issueToken.mock.calls[1][2]).toEqual(
    f.emailToken.issueToken.mock.calls[0][2],
  );
  expect(consumeMailDelivery).toHaveBeenCalledTimes(1);
  expect(f.user.getByMail).toHaveBeenCalledTimes(1);
  expect(f.rows.size).toBe(0);
  const logs = logger.child({ module: "test" });
  expect(JSON.stringify(jest.mocked(logs.warn).mock.calls)).not.toContain(
    "person@example.com",
  );
});

it("survives the crash-after-provider boundary by resending persisted content after lease recovery", async () => {
  const f = fixture();
  const id = await f.service().enqueue("person@example.com", "reset");
  f.authMail.complete.mockRejectedValueOnce(new Error("ack lost"));
  await f.service().processBatch();
  f.retryNow();
  await f.service().processBatch();
  expect(f.rows.has(id)).toBe(false);
  expect(f.sendgrid.sendMail.mock.calls[1][0]).toEqual(
    f.sendgrid.sendMail.mock.calls[0][0],
  );
});

it("does not send consumed recovery proofs and includes only the opaque challenge ID in recovery links", async () => {
  const f = fixture();
  const id = await f
    .service()
    .enqueue("person@example.com", "sign-in-recovery");
  await f.service().processBatch();
  const message = f.sendgrid.sendMail.mock.calls[0][0];
  expect(message.text).toContain("123456");
  expect(message.text).toContain(
    "https://example.com/auth/login/?recovery=rcv_private-challenge",
  );
  expect(message.text).not.toContain(`recovery=${id}`);
  expect(message.text).toContain("correct password is still required");
  expect(message.text).not.toContain("recovery=123456");
  jest.mocked(issueSignInRecoveryProof).mockResolvedValue(null);
  await f.service().enqueue("person@example.com", "sign-in-recovery");
  await f.service().processBatch();
  expect(f.sendgrid.sendMail).toHaveBeenCalledTimes(1);
});

it("rejects swapped kind or job ID authentication data before recipient lookup", async () => {
  const f = fixture();
  const id = await f.service().enqueue("person@example.com", "reset");
  f.rows.get(id)!.kind = "sign-in-recovery";
  await f.service().processBatch();
  expect(f.user.getByMail).not.toHaveBeenCalled();
  expect(f.sendgrid.sendMail).not.toHaveBeenCalled();
  expect(f.authMail.retry).toHaveBeenCalledTimes(1);
});

it("does not send from a lost lease and bounds each run to five claims", async () => {
  const f = fixture();
  for (let i = 0; i < 7; i++)
    await f.service().enqueue(`person${i}@example.com`, "reset");
  f.authMail.savePayload.mockResolvedValue(false);
  await f.service().processBatch();
  expect(f.authMail.claim).toHaveBeenCalledTimes(5);
  expect(f.sendgrid.sendMail).not.toHaveBeenCalled();
});

it("drops unknown recipients in the worker after the same durable enqueue path", async () => {
  const f = fixture();
  f.user.getByMail.mockResolvedValue(null as never);
  await f.service().enqueue("unknown@example.com", "reset");
  await f.service().processBatch();
  expect(f.rows.size).toBe(0);
  expect(f.emailToken.issueToken).not.toHaveBeenCalled();
  expect(f.sendgrid.sendMail).not.toHaveBeenCalled();
});

it("rechecks lease ownership after token storage before sending", async () => {
  const f = fixture();
  await f.service().enqueue("person@example.com", "reset");
  f.authMail.savePayload
    .mockResolvedValueOnce(true)
    .mockResolvedValueOnce(true)
    .mockResolvedValueOnce(false);
  await f.service().processBatch();
  expect(f.emailToken.issueToken).toHaveBeenCalledTimes(1);
  expect(f.sendgrid.sendMail).not.toHaveBeenCalled();
});

it("carries the encoded continuation and fragment inside next without adding recipient or code to the URL", async () => {
  const f = fixture();
  const next =
    "/ledger/owner/books/query?q=SELECT%20account%0AFROM%20accounts#results";
  await f.service().enqueue("person@example.com", "sign-in-recovery", next);
  await f.service().processBatch();
  const message = f.sendgrid.sendMail.mock.calls[0][0];
  const link = message.text!.match(/https:\/\/\S+/)![0];
  const parsed = new URL(link);
  expect(parsed.searchParams.get("recovery")).toBe("rcv_private-challenge");
  expect(parsed.searchParams.get("next")).toBe(next);
  expect(parsed.hash).toBe("");
  expect([...parsed.searchParams.keys()]).toEqual(["recovery", "next"]);
  expect(link).not.toContain("person@example.com");
  expect(link).not.toContain("123456");
  expect(message.html).toContain("&amp;next=");
});

it.each(["//evil.example", "/%2509/evil.example", "/" + "x".repeat(2048)])(
  "rejects an unsafe continuation before persisting a job: %s",
  async (next) => {
    const f = fixture();
    await expect(
      f.service().enqueue("person@example.com", "sign-in-recovery", next),
    ).rejects.toBeInstanceOf(BadUserInputError);
    expect(f.authMail.enqueue).not.toHaveBeenCalled();
    expect(f.user.getByMail).not.toHaveBeenCalled();
  },
);

it("revalidates an authenticated persisted continuation before constructing an email", async () => {
  const f = fixture();
  const id = await f
    .service()
    .enqueue("person@example.com", "sign-in-recovery");
  // Model a pre-existing authenticated payload from before validation changed;
  // the worker must validate data again even though GCM authentication passes.
  const key = Buffer.from(
    hkdfSync(
      "sha256",
      "synthetic-mail-test-secret",
      "",
      "beancount/auth-mail/v1",
      32,
    ),
  );
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  cipher.setAAD(Buffer.from(`${id}:sign-in-recovery:v1`));
  const encrypted = Buffer.concat([
    cipher.update(
      JSON.stringify({
        email: "person@example.com",
        returnTo: "//evil.example",
      }),
    ),
    cipher.final(),
  ]);
  f.rows.get(id)!.payload = [
    "v1",
    iv.toString("base64"),
    cipher.getAuthTag().toString("base64"),
    encrypted.toString("base64"),
  ].join(".");

  await f.service().processBatch();

  expect(f.sendgrid.sendMail).not.toHaveBeenCalled();
  expect(f.user.getByMail).not.toHaveBeenCalled();
  expect(f.authMail.retry).toHaveBeenCalledTimes(1);
});
