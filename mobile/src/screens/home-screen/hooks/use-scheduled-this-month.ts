import { useQueryShellQuery } from "@/generated-graphql/graphql";
import {
  hasScheduledRows,
  scheduledThisMonthBql,
} from "../selectors/scheduled-this-month";

/**
 * Whether the ledger has anything dated after `today` this month: one cheap
 * statement, the common answer being no, in which case Home keeps its stable
 * month-long window (w21/337). False while it loads or when it fails, so a
 * failure leaves Home reading what it did before.
 */
export function useScheduledThisMonth(
  ledgerId: string | null | undefined,
  today: string,
  skip = false,
): boolean {
  const { data } = useQueryShellQuery({
    variables: {
      ledgerId: ledgerId ?? "",
      query: scheduledThisMonthBql(today),
    },
    skip: skip || !ledgerId,
  });
  return hasScheduledRows(data?.queryShell?.table);
}
