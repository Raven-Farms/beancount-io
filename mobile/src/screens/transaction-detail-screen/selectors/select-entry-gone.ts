import { graphQLErrorCodes } from "../../../common/graphql-error-codes";

/**
 * Whether the entry context answered that this entry no longer exists — it
 * was changed (a new content hash) or removed by an agent, the CLI or the web
 * since the list was loaded. The screen then stops presenting the cached copy
 * as current and offers no link to it (w21/013). A network or server failure
 * is not "gone": it stays a retryable error.
 */
export function isEntryGone(contextError: unknown): boolean {
  return graphQLErrorCodes(contextError).includes("NOT_FOUND");
}

/**
 * Whether the ledger was written since the last check, read from
 * `ledgerRevisionVar`, which every invalidation bumps. A detail screen lower in
 * the stack kept showing an entry deleted or rewritten above it, because its
 * entry context is never evicted (w21/094); on focus it rechecks only when
 * this says so, so an unchanged ledger costs no request.
 */
export function createRevisionCheck(read: () => number): () => boolean {
  let seen = read();
  return () => {
    const now = read();
    if (now === seen) return false;
    seen = now;
    return true;
  };
}
