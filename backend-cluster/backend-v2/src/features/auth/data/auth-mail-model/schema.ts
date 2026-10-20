import { pgTable, text, integer, timestamp, index } from "drizzle-orm/pg-core";

/** Durable authentication mail. Addresses, codes and links exist only inside
 * authenticated ciphertext; rows are removed after delivery or expiration. */
export const authMail = pgTable(
  "auth_mail",
  {
    id: text("id").primaryKey(), // aem_ + Base58 nanoid
    kind: text("kind").$type<"reset" | "sign-in-recovery">().notNull(),
    payload: text("payload").notNull(),
    attempts: integer("attempts").notNull().default(0),
    availableAt: timestamp("available_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    leaseToken: text("lease_token"),
    leaseUntil: timestamp("lease_until", { withTimezone: true }),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (table) => [
    index("auth_mail_available_idx").on(table.availableAt),
    index("auth_mail_expiry_idx").on(table.expiresAt),
  ],
);
