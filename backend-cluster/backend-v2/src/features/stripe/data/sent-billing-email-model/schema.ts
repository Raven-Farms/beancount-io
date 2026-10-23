import { pgTable, text, timestamp } from "drizzle-orm/pg-core";

/**
 * Billing emails already sent, by a key naming what they announced (the
 * kind, the Stripe schedule, the scheduled price and its date). The row is
 * the claim that makes each email once-only across webhook retries, repeated
 * confirms and instances. It stores Stripe identifiers, never an address or
 * a name.
 */
export const sentBillingEmails = pgTable("sent_billing_emails", {
  key: text("key").primaryKey(),
  sentAt: timestamp("sent_at").notNull().defaultNow(),
});
