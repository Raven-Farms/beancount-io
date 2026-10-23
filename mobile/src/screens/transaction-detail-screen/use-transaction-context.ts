import { useCallback } from "react";
import {
  useGetLedgerEntryContextQuery,
  useGetLedgerTransactionContextQuery,
} from "@/generated-graphql/graphql";
import { isUnsupportedDocumentError } from "@/common/graphql-unsupported";

/**
 * The entry context transaction detail shows, with the ledger's `generated_from`
 * (w21/508): the source entry's hash when this entry is a copy a plugin or the
 * pad pass generated, null when it is not, and undefined until it loads or on a
 * server older than the field. Such a server rejects the whole document, so the
 * context is then read without it, as `useLedgerErrors` does (w21/591).
 */
export function useTransactionContext(
  variables: { entryHash: string; ledgerId: string },
  skip: boolean,
) {
  const full = useGetLedgerTransactionContextQuery({ variables, skip });
  const olderServer = isUnsupportedDocumentError(full.error);
  const basic = useGetLedgerEntryContextQuery({
    variables,
    skip: skip || !olderServer,
  });
  const source = olderServer ? basic : full;

  const fullRefetch = full.refetch;
  const basicRefetch = basic.refetch;
  const refetch = useCallback(
    () => (olderServer ? basicRefetch() : fullRefetch()),
    [olderServer, basicRefetch, fullRefetch],
  );

  return {
    data: source.data,
    loading: source.loading,
    error: source.error,
    refetch,
    generatedFrom: olderServer
      ? undefined
      : full.data?.getLedgerEntryContext?.generated_from,
  };
}
