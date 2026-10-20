import { and, eq, gt, gte, isNull, lt, lte, or, sql } from "drizzle-orm";
import type { DbExecutor } from "@/drizzle/drizzle";
import { prefixedNanoidBase58 } from "@/shared/nanoid-base58";
import { TTL } from "@/shared/cache";
import { authMail } from "./schema";
import type { AuthMail, IAuthMailModel } from "./types";

const MAX_ATTEMPTS = 5;
const now = sql`now()`;
function owned(mail: AuthMail) {
  return and(
    eq(authMail.id, mail.id),
    eq(authMail.leaseToken, mail.leaseToken!),
    gt(authMail.leaseUntil, now),
  );
}

export class AuthMailPostgresModel implements IAuthMailModel {
  async enqueue(
    db: DbExecutor,
    mail: Pick<AuthMail, "id" | "kind" | "payload" | "expiresAt">,
  ): Promise<void> {
    await db.insert(authMail).values(mail);
  }

  async claim(db: DbExecutor): Promise<AuthMail | null> {
    return db.transaction(async (tx) => {
      const [mail] = await tx
        .select()
        .from(authMail)
        .where(
          and(
            lt(authMail.attempts, MAX_ATTEMPTS),
            gt(authMail.expiresAt, now),
            lte(authMail.availableAt, now),
            or(isNull(authMail.leaseUntil), lte(authMail.leaseUntil, now)),
          ),
        )
        .orderBy(authMail.availableAt, authMail.id)
        .limit(1)
        .for("update", { skipLocked: true });
      if (!mail) return null;
      const [claimed] = await tx
        .update(authMail)
        .set({
          attempts: sql`${authMail.attempts} + 1`,
          leaseToken: prefixedNanoidBase58("aml_"),
          leaseUntil: sql`now() + ${TTL.MIN_1} * interval '1 millisecond'`,
        })
        .where(eq(authMail.id, mail.id))
        .returning();
      return claimed;
    });
  }

  async savePayload(
    db: DbExecutor,
    mail: AuthMail,
    payload: string,
  ): Promise<boolean> {
    const rows = await db
      .update(authMail)
      .set({
        payload,
        leaseUntil: sql`now() + ${TTL.MIN_1} * interval '1 millisecond'`,
      })
      .where(and(owned(mail), gt(authMail.expiresAt, now)))
      .returning({ id: authMail.id });
    return rows.length === 1;
  }

  async complete(db: DbExecutor, mail: AuthMail): Promise<void> {
    await db.delete(authMail).where(owned(mail));
  }

  async retry(db: DbExecutor, mail: AuthMail): Promise<void> {
    if (mail.attempts >= MAX_ATTEMPTS) return this.complete(db, mail);
    const delay = Math.min(TTL.MIN_1, 5_000 * 2 ** (mail.attempts - 1));
    await db
      .update(authMail)
      .set({
        availableAt: sql`now() + ${delay} * interval '1 millisecond'`,
        leaseToken: null,
        leaseUntil: null,
      })
      .where(owned(mail));
  }

  async cleanup(db: DbExecutor): Promise<void> {
    await db
      .delete(authMail)
      .where(
        and(
          or(
            lte(authMail.expiresAt, now),
            gte(authMail.attempts, MAX_ATTEMPTS),
          ),
          or(isNull(authMail.leaseUntil), lte(authMail.leaseUntil, now)),
        ),
      );
  }
}
