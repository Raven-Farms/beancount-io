/**
 * Ranking for the Home budget panel. The panel has room for a few rows, so it
 * shows the budgets closest to (or past) their limit rather than the first few
 * alphabetically — the ones worth knowing about before you spend again.
 */
import { dropRoot } from "../../../common/account-util";
import { formatMoneyWithCurrency } from "../../../common/number-utils";
import {
  budgetDirection,
  calculateBudgetForInterval,
} from "../../budget-screen/selectors/budget-selectors";
import type { BudgetGroup } from "../../budget-screen/selectors/budget-selectors";
import { selectBudgetCardStats } from "../../budget-screen/selectors/select-budget-card-stats";

export type BudgetPanelInput = {
  group: BudgetGroup;
  /** Actual activity for the current period, or null when it hasn't loaded. */
  actual: number | null;
  /** Last day of the period the actual covers. */
  periodEnd: string;
};

export type BudgetPanelRow = {
  account: string;
  shortAccount: string;
  currency: string;
  /** Budget for the current period, as a magnitude. */
  budget: number;
  /** Actual for the same period, sign-corrected to match. */
  actual: number;
  /**
   * Spend as a percentage of budget, clamped at 0. A budget of 0 has nothing
   * to divide by: 100 (a full meter) once anything is spent, else 0.
   */
  progressPercent: number;
  /** A budget of 0 or less, so `progressPercent` is no percentage to read out. */
  noBudget: boolean;
  /** True when this budget is on the good side of its target. */
  favorable: boolean;
};

/**
 * @param asOf - Today. A period still in progress is budgeted only up to it,
 *   as the Budget screen does, so the row and the screen agree (w21/076).
 */
export function selectBudgetPanelRows(
  inputs: BudgetPanelInput[],
  limit: number,
  asOf?: string,
): BudgetPanelRow[] {
  const rows = inputs.map(({ group, actual, periodEnd }) => {
    // Reuse the card's derivation so the two surfaces can't drift on the
    // favorability rules. It reads a series, so hand it the single period the
    // panel cares about, sign-corrected the way the card's series already is.
    const direction = budgetDirection(group.value);
    const stats = selectBudgetCardStats(group, [
      {
        date: periodEnd,
        actual: (actual ?? 0) * direction,
        budget:
          calculateBudgetForInterval(
            periodEnd,
            group.interval,
            group.budgetHistory,
            asOf,
          ) * direction,
      },
    ]);
    const spent = stats.actual ?? 0;
    const noBudget = stats.budget <= 0;

    return {
      account: group.account,
      shortAccount: dropRoot(group.account),
      currency: group.currency,
      budget: stats.budget,
      actual: spent,
      progressPercent: noBudget
        ? spent > 0
          ? 100
          : 0
        : (stats.progressPercent ?? 0),
      noBudget,
      favorable: stats.favorable,
    };
  });

  // Highest utilization first, and a 0 budget already spent past it before
  // everything else: it read "0% used" and sorted last (w21/076). Ties break on
  // account so the order is stable between renders rather than depending on
  // query completion order.
  const rank = (row: BudgetPanelRow) =>
    row.noBudget && row.actual > 0 ? Infinity : row.progressPercent;
  return rows
    .sort((a, b) => rank(b) - rank(a) || a.account.localeCompare(b.account))
    .slice(0, limit);
}

/**
 * What a panel row announces beyond its account name.
 *
 * The row is one button wrapping the amounts and the meter, so an
 * `accessibilityLabel` on it collapses the subtree and hides every number a
 * sighted user reads. The label stays the account; this goes in
 * `accessibilityValue.text`, which VoiceOver speaks after the label — so it
 * repeats neither the account nor anything the label already says.
 *
 * Pure and string-only: the same `formatMoneyWithCurrency` the row renders, so
 * the spoken amounts cannot drift from the visible ones.
 */
export function budgetPanelRowAccessibilityValue(
  row: BudgetPanelRow,
  t: (key: string, options?: Record<string, string | number>) => string,
): string {
  const status = t(row.favorable ? "budgetBelowTarget" : "budgetAboveTarget");
  if (row.noBudget) {
    return t("budgetPanelRowValueNoBudget", {
      actual: formatMoneyWithCurrency(row.actual, row.currency),
      budget: formatMoneyWithCurrency(row.budget, row.currency),
      status,
    });
  }
  return t("budgetPanelRowValue", {
    actual: formatMoneyWithCurrency(row.actual, row.currency),
    budget: formatMoneyWithCurrency(row.budget, row.currency),
    // Whole percent: a spoken "73.4166 percent" is noise, and the meter it
    // describes is a bar, not a readout.
    percent: Math.round(row.progressPercent),
    status,
  });
}
