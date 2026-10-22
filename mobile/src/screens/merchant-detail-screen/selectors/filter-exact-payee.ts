/**
 * Exact payee match over journal entries. `getLedgerJournal`'s `query.filter`
 * is free-text search, so callers must re-filter client-side (same pattern as
 * `use-two-posting-suggestions`).
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */

import { toPlainSearchFilter } from "../../transactions-screen/utils/plain-search-filter";

/** The longest filter pattern the ledger service accepts. */
const MAX_FILTER_PATTERN_LENGTH = 256;

export interface PayeeBearing {
  payee?: string | null;
}

/**
 * Keep only entries whose payee equals one of `payees` exactly (after trim):
 * every spelling a merged Merchants row counted (w21/046).
 */
export function filterExactPayee<T extends PayeeBearing>(
  entries: readonly T[],
  payees: string | readonly string[],
): T[] {
  const targets = new Set(
    (typeof payees === "string" ? [payees] : payees)
      .map((payee) => payee.trim())
      .filter(Boolean),
  );
  if (targets.size === 0) {
    return [];
  }
  return entries.filter((entry) => targets.has((entry.payee ?? "").trim()));
}

/**
 * The `otherSpellings` route param: a JSON array of strings, or nothing. A
 * deep link can carry anything, so anything else reads as no other spellings.
 */
export function parseSpellings(raw: string | string[] | undefined): string[] {
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (!value) return [];
  try {
    const parsed: unknown = JSON.parse(value);
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === "string")
      : [];
  } catch {
    return [];
  }
}

/**
 * The journal filter that selects exactly a merchant's payee spellings: an
 * anchored payee expression, padded for the trailing space a bank import
 * leaves (w21/093). Free-text on the payee also matched narrations and longer
 * payees ("Ace" among "Ace Deli"), and paging stopped after 500 of those, so
 * the merchant's own rows vanished (w21/181). Case differences still pass the
 * server's matcher; `filterExactPayee` narrows them on the client.
 */
export function exactPayeeFilter(
  payees: readonly string[],
): string | undefined {
  // The server matches case-insensitively, so spellings that differ only in
  // case or in trailing space are one alternative (w21/361).
  const seen = new Set<string>();
  const spellings = payees
    .map((payee) => payee.trim())
    .filter((payee) => {
      const key = payee.toLowerCase();
      if (!payee || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  if (spellings.length === 0) return undefined;
  const alternatives = spellings
    .map((payee) => payee.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    // The filter's string literal has no escapes, so a quote is spelled \x22.
    .map((payee) => payee.replace(/"/g, "\\x22"));
  const pattern = `^\\s*(?:${alternatives.join("|")})\\s*$`;
  // The ledger service refuses a pattern longer than this, which failed the
  // whole journal for a merchant with long merged spellings. Fall back to
  // matching the primary spelling as text; `filterExactPayee` still narrows
  // the rows on the client.
  return pattern.length > MAX_FILTER_PATTERN_LENGTH
    ? toPlainSearchFilter(spellings[0])
    : `payee:"${pattern}"`;
}
