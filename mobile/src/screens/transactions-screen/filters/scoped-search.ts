/**
 * The Transactions search text, kept with the ledger it was typed in. The tab
 * stays mounted across a ledger switch, so a search typed on one ledger went
 * on narrowing the next one's journal, often to "No transactions match"
 * (w21/114), the way w3/115 found the filters doing.
 */
export type ScopedSearch = { ledgerId: string; text: string };

/** The search for `ledgerId`: its own text, or none after a switch. */
export function searchForLedger(
  search: ScopedSearch,
  ledgerId: string,
): string {
  return search.ledgerId === ledgerId ? search.text : "";
}
