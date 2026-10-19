import type { DbExecutor } from "@/drizzle/drizzle";

export interface ISentBillingEmailModel {
  /** Claim an email by key. True only for the first caller. */
  claim(db: DbExecutor, key: string): Promise<boolean>;
  /** Give a claim back after a failed send, so a retry can send it. */
  release(db: DbExecutor, key: string): Promise<void>;
}
