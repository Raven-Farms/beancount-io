import { useMemo } from "react";
import { useLedgerAccountCloseDatesQuery } from "@/generated-graphql/graphql";
import { closeDatesOf, type CloseDates } from "../account-close-dates";

/**
 * Close dates of the ledger's accounts, for the posting pickers and the payee
 * autofill (w21/045). Empty until they load, which leaves every account
 * offered — the server still refuses a closed one at Done.
 */
export function useAccountCloseDates(ledgerId: string | undefined): CloseDates {
  const { data } = useLedgerAccountCloseDatesQuery({
    variables: { ledgerId: ledgerId ?? "" },
    skip: !ledgerId,
    fetchPolicy: "cache-and-network",
  });
  return useMemo(() => closeDatesOf(data?.getLedgerAccountDirectives), [data]);
}
