import type { ApolloCache } from "@apollo/client";
import { GetLedgerDocument } from "@/graphql/definitions";

/**
 * Record a confirmed star/unstar in the cached ledger. The mutation's own
 * `isStarred` is the authority, and starring changes no other field, so there
 * is no read to fail after an acknowledged write (w4/m41).
 */
export function writeStarredState(
  cache: ApolloCache,
  ledgerId: string,
  result: { success: boolean; isStarred: boolean } | undefined,
) {
  if (!result?.success) return;
  cache.updateQuery(
    { query: GetLedgerDocument, variables: { ledgerId } },
    (current) =>
      current?.getLedger
        ? {
            ...current,
            getLedger: { ...current.getLedger, isStarred: result.isStarred },
          }
        : current,
  );
}
