/**
 * Append a fetched journal page to the rows already loaded. Paging is by
 * offset, so an entry added elsewhere while the user scrolls shifts the next
 * page down by one and its first row repeats the last one loaded (w21/035).
 * Each `entry_hash` is kept once, and `overlapped` reports the shift so the
 * screen can reload from the top, where the new entry now sits.
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */
export function mergeJournalPage<T extends { entry_hash?: string | null }>(
  loaded: readonly T[],
  page: readonly T[],
): { data: T[]; overlapped: boolean } {
  const seen = new Set(loaded.map((row) => row.entry_hash));
  const data = [...loaded];
  let overlapped = false;
  for (const row of page) {
    if (row.entry_hash != null && seen.has(row.entry_hash)) {
      overlapped = true;
      continue;
    }
    seen.add(row.entry_hash);
    data.push(row);
  }
  return { data, overlapped };
}

/**
 * What a journal list is, beyond its paging. Apollo runs a load-more page's
 * `updateQuery` against the query's variables when the page lands, so a page
 * requested before a filter change or ledger switch was appended to the new
 * list, its total included (w21/116); a screen compares this key from the
 * request with the one current when the page arrives.
 */
export function journalListKey(ledgerId: string, query: object): string {
  return JSON.stringify([ledgerId, query]);
}
