import { logger } from "@/shared/logger";

/**
 * The ledger service relays Gitea's lists, and Gitea serves them in pages of
 * at most `API.MAX_RESPONSE_ITEMS` (50, which this deployment does not
 * override): a larger `limit` is clamped without a word, and an omitted one
 * falls back to `DEFAULT_PAGING_NUM` (30). A read that must not lose entries
 * pages through at this size (w2/m34), and a shorter page is the last one.
 */
export const GITEA_PAGE_SIZE = 50;
// A runaway guard for an upstream that never returns a short page, not a
// product limit: 10,000 entries.
const MAX_PAGES = 200;

/**
 * Read a Gitea-backed list from `firstPage` until a short page, or until
 * `enough` says the caller has what it needs.
 */
export async function readGiteaPages<T>(
  readPage: (query: { page: number; limit: number }) => Promise<T[]>,
  {
    firstPage = 1,
    enough = () => false,
  }: { firstPage?: number; enough?: (read: readonly T[]) => boolean } = {},
): Promise<T[]> {
  const items: T[] = [];
  for (let read = 0; !enough(items); read++) {
    if (read === MAX_PAGES) {
      logger.warn("Gitea list read hit the page cap and may be truncated", {
        firstPage,
        items: items.length,
      });
      break;
    }
    const batch = await readPage({
      page: firstPage + read,
      limit: GITEA_PAGE_SIZE,
    });
    items.push(...batch);
    if (batch.length < GITEA_PAGE_SIZE) break;
  }
  return items;
}
