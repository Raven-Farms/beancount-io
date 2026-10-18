import { pgTable, text, timestamp } from "drizzle-orm/pg-core";

/**
 * Paid invoices already reported to analytics as a `purchase`. The row is the
 * claim that makes the report once-only across webhook retries and
 * instances; it holds no user or customer data.
 */
export const reportedPurchases = pgTable("reported_purchases", {
  invoiceId: text("invoice_id").primaryKey(),
  reportedAt: timestamp("reported_at").notNull().defaultNow(),
});
