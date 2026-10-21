import type { ApolloCache } from "@apollo/client";
import { GetLedgerDocument } from "@/graphql/definitions";

/**
 * Record a confirmed star/unstar in the cached ledger.
 *
 * The mutation's own `isStarred` is the authority. An awaited GetLedger
 * refetch used to be part of the mutation, so a failed read rejected an
 * already acknowledged star and the button rolled it back (w4/m41). Starring
 * changes no other ledger field, so nothing needs reading again.
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
