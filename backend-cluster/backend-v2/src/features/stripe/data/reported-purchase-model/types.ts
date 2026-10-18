import type { DbExecutor } from "@/drizzle/drizzle";

export interface IReportedPurchaseModel {
  /**
   * Claim a paid invoice for reporting. True only for the first caller, so a
   * retried or duplicate webhook delivery reports nothing.
   */
  claim(db: DbExecutor, invoiceId: string): Promise<boolean>;
  /** Give a claim back after a failed send, so Stripe's retry can report it. */
  release(db: DbExecutor, invoiceId: string): Promise<void>;
}
