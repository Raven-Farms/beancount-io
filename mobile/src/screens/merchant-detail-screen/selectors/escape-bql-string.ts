/**
 * A BQL predicate matching `payee` exactly, safe for any payee text.
 *
 * The ledger's rustledger engine reads a double-quoted string literal with no
 * escape processing, so `\"` is a syntax error and SQL-style `''` is not an
 * escape either: a payee containing `"` dropped the merchant header with a
 * parse error (w21/032). An ordinary payee is compared with `=` as before.
 * One containing `"` or `\` becomes an anchored regex instead, metacharacters
 * escaped and `"` written as the regex escape `\x22`, the same encoding
 * Transactions search uses (`plain-search-filter.ts`).
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */
export function bqlPayeeEquals(payee: string): string {
  if (!/["\\]/.test(payee)) return `payee = "${payee}"`;
  const pattern = payee
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/"/g, "\\x22");
  return `payee ~ "^${pattern}$"`;
}
