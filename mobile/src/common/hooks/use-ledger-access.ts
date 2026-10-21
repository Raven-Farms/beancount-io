import { useReactiveVar } from "@apollo/client";
import { ledgerVar } from "@/common/vars";
import { useGetLedgerQuery } from "@/generated-graphql/graphql";
import { selectCanWrite } from "@/common/ledger-access";
import { useGuest } from "@/common/guest/guest-context";

export function useLedgerAccess() {
  const guest = useGuest();
  const ledgerId = useReactiveVar(ledgerVar);
  const { data, error, loading, refetch } = useGetLedgerQuery({
    variables: { ledgerId: ledgerId ?? "" },
    skip: !!guest || !ledgerId,
    fetchPolicy: "cache-and-network",
  });
  return {
    canWrite: selectCanWrite({ guest: !!guest, ledgerId, data, error }),
    loading,
    error,
    refetch,
  };
}
