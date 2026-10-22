/**
 * Append a fetched journal page to the rows already loaded. Paging is by
 * offset, so an entry added elsewhere while the user scrolls shifts the next
 * page down by one and its first row repeats the last one loaded (w21/035).
 * That is told by the list's `total` having changed since the rows were loaded:
 * then each `entry_hash` is kept once and `overlapped` reports the shift so the
 * screen can reload from the top, where the new entry now sits.
 *
 * With the total unchanged nothing moved, and a repeated hash is a real second
 * entry, not an overlap: two identical entries (two $4.50 coffees, same payee,
 * same day) hash alike, and dropping the twin read as "the list moved" and
 * reloaded from the top on every page, forever (w21/419). Rows are appended
 * as they are.
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */
export function mergeJournalPage<T extends { entry_hash?: string | null }>(
  loaded: readonly T[],
  page: readonly T[],
  totals?: { loaded?: number | null; page?: number | null },
): { data: T[]; overlapped: boolean } {
  const moved =
    totals?.loaded != null &&
    totals?.page != null &&
    totals.loaded !== totals.page;
  if (!moved) return { data: [...loaded, ...page], overlapped: false };
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
 * A React key per row: its `entry_hash`, and for each further row with the same
 * hash (an identical twin) the hash and its ordinal, so twins on one screen do
 * not share a key (w21/419).
 */
export function journalRowKeys<T extends { entry_hash?: string | null }>(
  rows: readonly T[],
): Map<T, string> {
  const counts = new Map<string, number>();
  const keys = new Map<T, string>();
  rows.forEach((row, index) => {
    const hash = row.entry_hash ?? `row:${index}`;
    const n = counts.get(hash) ?? 0;
    counts.set(hash, n + 1);
    keys.set(row, n === 0 ? hash : `${hash}#${n}`);
  });
  return keys;
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
