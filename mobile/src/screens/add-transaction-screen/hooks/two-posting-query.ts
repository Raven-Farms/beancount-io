import { toPlainSearchFilter } from "../../transactions-screen/utils/plain-search-filter";

/**
 * The journal query behind a payee's usual accounts. The payee goes out as a
 * quoted filter string: raw, the server parsed it as filter syntax and
 * refused `Dupar's`, `Mr. Marcel` or `Chase:Slate`, so their accounts were
 * never seeded (w21/149). Callers still exact-match the payee client-side.
 */
export function twoPostingSuggestionsQuery(payee: string) {
  return { filter: toPlainSearchFilter(payee), limit: 50 };
}
