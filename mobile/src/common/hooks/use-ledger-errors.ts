import { useCallback } from "react";
import { useReactiveVar } from "@apollo/client";
import { ledgerVar } from "@/common/vars";
import {
  useGetLedgerErrorsBasicQuery,
  useGetLedgerErrorsQuery,
} from "@/generated-graphql/graphql";
import type { LedgerError } from "@/common/new-ledger-error";
import {
  basicLedgerErrors,
  isUnknownFieldError,
} from "@/common/ledger-errors-read";

export const useLedgerErrors = (selectedLedgerId?: string) => {
  const accountLedgerId = useReactiveVar(ledgerVar);
  const ledgerId = selectedLedgerId ?? accountLedgerId;
  const full = useGetLedgerErrorsQuery({
    variables: { ledgerId: ledgerId ?? "" },
    skip: !ledgerId,
    fetchPolicy: "cache-and-network",
  });
  // A server older than the app rejects the `code` and `hint` it asks for: read
  // the errors without them, so a broken ledger still shows as broken (w21/591).
  const olderServer = isUnknownFieldError(full.error);
  const basic = useGetLedgerErrorsBasicQuery({
    variables: { ledgerId: ledgerId ?? "" },
    skip: !ledgerId || !olderServer,
    fetchPolicy: "cache-and-network",
  });
  const source = olderServer ? basic : full;

  const errors: LedgerError[] =
    (olderServer
      ? basicLedgerErrors(basic.data)
      : full.data?.getLedgerErrors) ?? [];

  const fullRefetch = full.refetch;
  const basicRefetch = basic.refetch;
  const refetch = useCallback(
    () => (olderServer ? basicRefetch() : fullRefetch()),
    [olderServer, basicRefetch, fullRefetch],
  );

  return {
    errors,
    count: errors.length,
    loading: source.loading,
    /** Whether a result has arrived: an empty `errors` cannot tell "none" from "not yet". */
    loaded: source.data !== undefined,
    error: source.error,
    refetch,
  };
};
