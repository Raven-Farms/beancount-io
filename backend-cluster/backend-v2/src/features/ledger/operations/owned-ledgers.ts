import { type FavaApiClient, unwrapFavaResponse } from "@/foundation/fava";
import { readGiteaPages } from "@/shared/gitea-pages";

/**
 * How many ledgers `username` owns. It reads the owner's own list, every
 * page, so collaborated and organization ledgers never count and a
 * difference in letter case cannot hide one. With `stopAt`, it stops reading
 * once the count reaches it.
 */
export async function countOwnedLedgers(
  favaApiClient: FavaApiClient,
  username: string,
  {
    stopAt = Infinity,
    makeError,
  }: { stopAt?: number; makeError?: (cause?: unknown) => Error } = {},
): Promise<number> {
  const owned = await readGiteaPages(
    (query) =>
      unwrapFavaResponse(
        favaApiClient.ledgers.listUserLedgers(username, query),
        "list ledgers",
        makeError,
      ),
    { enough: (read) => read.length >= stopAt },
  );
  return owned.length;
}
