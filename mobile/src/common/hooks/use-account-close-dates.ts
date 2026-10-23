import { useMemo } from "react";
import { useLedgerAccountCloseDatesQuery } from "@/generated-graphql/graphql";
import { closeDatesOf, type CloseDates } from "../account-close-dates";

/**
 * Close dates of the ledger's accounts, and whether they have arrived. Empty
 * until they load, which leaves every account offered — the server still
 * refuses a closed one at Done. A failed read counts as settled.
 */
export function useAccountCloseDatesState(ledgerId: string | undefined): {
  closeDates: CloseDates;
  settled: boolean;
} {
  const { data, error } = useLedgerAccountCloseDatesQuery({
    variables: { ledgerId: ledgerId ?? "" },
    skip: !ledgerId,
    fetchPolicy: "cache-and-network",
  });
  const closeDates = useMemo(
    () => closeDatesOf(data?.getLedgerAccountDirectives),
    [data],
  );
  return { closeDates, settled: data !== undefined || Boolean(error) };
}

/**
 * Close dates of the ledger's accounts, for the posting pickers and the payee
 * autofill (w21/045).
 */
export function useAccountCloseDates(ledgerId: string | undefined): CloseDates {
  return useAccountCloseDatesState(ledgerId).closeDates;
}
