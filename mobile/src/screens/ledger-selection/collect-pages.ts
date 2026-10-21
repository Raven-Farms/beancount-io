/**
 * Every page of an account list, so local search never searches page one
 * only. Pages until one comes back short: the starred list's `total` is the
 * returned page's own length (a backend contract), so stopping at `total` cut
 * Starred off at 30 ledgers (w21/129). A server that ignores the page number
 * and repeats a full page stops here instead of looping forever.
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */
export async function collectPages<T>(
  fetchPage: (page: number) => Promise<T[]>,
  pageSize: number,
  keyOf: (item: T) => string,
  signal?: AbortSignal,
): Promise<T[]> {
  const items: T[] = [];
  const seen = new Set<string>();
  for (let page = 1; ; page++) {
    if (signal?.aborted) throw new Error("Discovery request cancelled");
    const rows = await fetchPage(page);
    const fresh = rows.filter((row) => !seen.has(keyOf(row)));
    for (const row of fresh) seen.add(keyOf(row));
    items.push(...fresh);
    if (rows.length < pageSize || fresh.length === 0) return items;
  }
}
