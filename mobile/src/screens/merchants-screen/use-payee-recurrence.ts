import { useMemo } from "react";
import { useQueryShellQuery } from "@/generated-graphql/graphql";
import { useToday } from "@/common/hooks/use-today";
import { useLedgerRootNames } from "@/common/hooks/use-ledger-root-names";
import { seriesByMerchant } from "@/common/merchant-key";
import {
  detectRecurrence,
  hasEnoughHistory,
} from "./selectors/detect-recurrence";
import {
  buildPayeeSeriesBql,
  mapPayeeSeries,
  payeeSeriesCutoff,
} from "./selectors/payee-series";

/**
 * Shared windowed series fetch + per-merchant detection for the merchants
 * directory and merchant detail, keyed by `merchantKey`. One `queryShell` round
 * trip. `today` is the watched day (`useToday`): it moves only at midnight, so
 * Overdue turns on without a remount and cannot flicker within a day (w21/233).
 */
export function usePayeeRecurrence(ledgerId: string | null | undefined) {
  const today = useToday();
  const seriesCutoff = useMemo(() => payeeSeriesCutoff(today), [today]);
  const { expenses, income } = useLedgerRootNames();
  const seriesBql = useMemo(
    () =>
      seriesCutoff
        ? buildPayeeSeriesBql(seriesCutoff, { expenses, income })
        : null,
    [seriesCutoff, expenses, income],
  );

  const query = useQueryShellQuery({
    variables: {
      ledgerId: ledgerId!,
      query: seriesBql ?? "",
    },
    skip: !ledgerId || !seriesBql,
  });

  const { detections, enoughHistory } = useMemo(() => {
    // Keyed by merchant, every spelling's events together (w21/169).
    const seriesByPayee = seriesByMerchant(
      mapPayeeSeries(query.data?.queryShell?.table ?? null, {
        expenses,
        income,
      }),
    );
    const map = new Map<string, ReturnType<typeof detectRecurrence>>();
    // Payees with enough dates to analyse: a manual mark on any other reads
    // "Not enough history", not "Irregular" (w0/039).
    const enough = new Set<string>();
    for (const [payee, series] of seriesByPayee) {
      map.set(payee, detectRecurrence(series, today));
      if (hasEnoughHistory(series)) enough.add(payee);
    }
    return { detections: map, enoughHistory: enough };
  }, [query.data?.queryShell?.table, today, expenses, income]);

  return { ...query, today, detections, enoughHistory, seriesBql };
}
