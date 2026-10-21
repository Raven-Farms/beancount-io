import { useMemo } from "react";
import { useGetLedgerIntervalTotalsQuery } from "@/generated-graphql/graphql";
import { resolveCurrencyBalance } from "@/common/balance-util";
import { getFormatDate } from "@/common/format-util";
import {
  budgetForInterval,
  periodsThrough,
  throughCurrentPeriod,
  prepareBudgetHistory,
  type BudgetGroup,
} from "@/screens/budget-screen/selectors/budget-selectors";
import type { BudgetSeriesPoint } from "@/screens/budget-screen/selectors/select-budget-card-stats";
import { timeWindowStart } from "@/screens/budget-screen/selectors/budget-labels";

/**
 * Budget compares raw account activity, so it asks fava for `units` rather than
 * the `at_cost` valuation the balance charts use — a budget is written in one
 * currency and measured against postings in that same currency.
 */
const BUDGET_CONVERSION = "units";

/**
 * Shared variables so the budget page and the Home panel land on the same
 * Apollo cache entry. That sharing depends on the two being byte-identical,
 * which is not something two hand-written copies can guarantee — same reason
 * `budgetJournalVariables` exists for the directives query.
 */
export function budgetTotalsVariables({
  ledgerId,
  group,
  time,
}: {
  ledgerId: string;
  group: BudgetGroup;
  time?: string;
}) {
  return {
    ledgerId,
    accountName: group.account,
    interval: group.interval.toLowerCase(),
    conversion: BUDGET_CONVERSION,
    time,
  };
}

/**
 * Per-interval actuals for one budget group, paired with the prorated budget
 * for each period. `getLedgerIntervalTotals` rolls sub-accounts into the parent
 * server-side, matching fava (and the dashboard): actuals include children,
 * budgets bind to the exact account.
 */
export function useBudgetActuals({
  ledgerId,
  group,
  currency,
  time,
  direction,
}: {
  ledgerId: string;
  group: BudgetGroup;
  currency: string;
  time?: string;
  direction: 1 | -1;
}) {
  const { data, loading, error } = useGetLedgerIntervalTotalsQuery({
    variables: budgetTotalsVariables({ ledgerId, group, time }),
  });

  const series: BudgetSeriesPoint[] = useMemo(() => {
    // Actuals stop at today, so the budget they are measured against does too.
    const today = getFormatDate(new Date());
    const fetched = data?.getLedgerIntervalTotals ?? [];
    // All time runs to the last posting, even a future one (w21/168).
    const items =
      time === undefined
        ? throughCurrentPeriod(fetched, group.interval, today)
        : fetched;
    // Prepared once per group: `budgetForInterval` runs per charted period, and
    // the `all` span can return a hundred of them.
    const history = prepareBudgetHistory(group.budgetHistory);
    // And start where the window does: its first period is often partial.
    const windowStart = timeWindowStart(time, today);
    const point = (date: string, actual: number) => ({
      date,
      actual: actual * direction,
      budget:
        budgetForInterval(date, group.interval, history, today, windowStart) *
        direction,
    });
    const points = items.map((item) =>
      point(item.date, resolveCurrencyBalance(item.balance, currency)),
    );
    // A windowed range ends today on the server. All time ends at the last
    // posting, so carry it on through today with the periods nothing was
    // spent in, as YTD and 1Y show them (w21/010).
    const last = items[items.length - 1];
    if (time === undefined && last) {
      for (const date of periodsThrough(last.date, group.interval, today)) {
        points.push(point(date, 0));
      }
    }
    return points;
  }, [data, currency, direction, group.interval, group.budgetHistory, time]);

  return { series, loading, error };
}
