/**
 * The budget directives after the first page: every offset from `have` up to
 * `total`, one page at a time, newest first as the server returns them. A page
 * that comes back empty before `total` is reached is an error: the set cannot be
 * completed, and a partial one would compare against the wrong targets
 * (w21/397).
 *
 * `readPage` is injected so this is a plain function over plain values, which
 * the jest-lite runner can load.
 */
export async function readBudgetPages(
  have: number,
  total: number,
  pageSize: number,
  readPage: (offset: number) => Promise<unknown[]>,
): Promise<unknown[]> {
  const pages: unknown[] = [];
  for (let offset = have; offset < total; offset += pageSize) {
    const page = await readPage(offset);
    if (page.length === 0) throw new Error("Budget history ended early");
    pages.push(...page);
  }
  return pages;
}
