import { useCallback } from "react";
import { useApolloClient } from "@apollo/client/react";
import { GetLedgerDirContentDocument } from "@/graphql/definitions";

/**
 * Re-read a folder after a file write. The write already succeeded; this read
 * is separate from it, so a failure here never marks the file unwritten or
 * invites creating it again (w4/248). When the read fails the cached listing
 * is dropped instead, so the folder reads afresh — or shows its own error —
 * where it is next displayed, rather than listing a stale directory.
 */
export function useRefreshDirectory(ledgerId: string, dirPath: string) {
  const client = useApolloClient();
  return useCallback(async () => {
    const variables = { ledgerId, dirPath: dirPath || null };
    try {
      await client.query({
        query: GetLedgerDirContentDocument,
        variables,
        fetchPolicy: "network-only",
      });
    } catch {
      client.cache.evict({ fieldName: "getLedgerDirContent", args: variables });
      client.cache.gc();
    }
  }, [client, ledgerId, dirPath]);
}
