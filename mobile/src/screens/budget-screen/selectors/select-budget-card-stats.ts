/**
 * Derives the numbers a budget card shows from a group and its actuals series.
 * Pure so the jest-lite runner can exercise the favorability rules, which are
 * the easiest part of budget to get subtly wrong (income budgets invert them).
 */
import {
  groupDirection,
  budgetScale,
  isFavorableVariance,
  varianceStatus,
  type BudgetGroup,
  type VarianceStatus,
} from "./budget-selectors";

export type BudgetSeriesPoint = {
  date: string;
  /** Actual activity, sign-corrected so expenses and income both read positive. */
  actual: number;
  /** Prorated budget for the same period, same sign convention. */
  budget: number;
};

export type BudgetCardStats = {
  /** Budget for the latest charted period, as a magnitude. */
  budget: number;
  /** Actual activity for that period, or null when the series is empty. */
  actual: number | null;
  /** actual − budget; positive means above target. */
  variance: number | null;
  status: VarianceStatus | null;
  /** True when the variance falls on the good side for this budget's kind. */
  favorable: boolean;
  /** Spend as a percentage of budget, or null when there is nothing to divide by. */
  progressPercent: number | null;
  /**
   * The first directive's date when the latest period ended before it: no
   * target existed yet, so nothing is judged (w21/101).
   */
  startsOn: string | null;
};

/** The earliest directive's date, or null with no history. */
function firstBudgetDate(
  budgetHistory: readonly { date: string }[],
): string | null {
  return budgetHistory.reduce<string | null>(
    (first, entry) =>
      first === null || entry.date < first ? entry.date : first,
    null,
  );
}

/**
 * A period with no target to miss: it ended before the first directive, or the
 * first directive has not started yet (dated after `today`, so the period holds
 * a zero budget that is no target at all). A period the first directive falls
 * in carries a back-filled target and is judged against it (w21/301).
 */
function beforeFirstBudget(
  point: BudgetSeriesPoint,
  firstBudget: string | null,
  today?: string,
): boolean {
  if (point.budget !== 0 || firstBudget === null) return false;
  return (
    point.date < firstBudget || (today !== undefined && firstBudget > today)
  );
}

/**
 * Whether each charted period landed on the good side of its own budget. Same
 * rule as the card's status badge — money tolerance and income inversion
 * included — so a bar can't contradict the badge sitting above it.
 *
 * `null` for a period that ended before the first budget directive: there was
 * no target to miss, yet its zero budget made any spending read as over, so a
 * new budget always looked behind on first view (w21/033). An explicit zero
 * budget is a target and is still judged.
 */
export function selectPointFavorability(
  series: BudgetSeriesPoint[],
  direction: 1 | -1,
  budgetHistory: readonly { date: string; amount?: string }[] = [],
  today?: string,
): (boolean | null)[] {
  const firstBudget = firstBudgetDate(budgetHistory);
  const scale = budgetScale(budgetHistory);
  return series.map((point) =>
    beforeFirstBudget(point, firstBudget, today)
      ? null
      : isFavorableVariance(
          varianceStatus(point.actual - Math.abs(point.budget), scale),
          direction,
        ),
  );
}

export function selectBudgetCardStats(
  group: BudgetGroup,
  series: BudgetSeriesPoint[],
  today?: string,
): BudgetCardStats {
  const direction = groupDirection(group);
  const latest = series.length > 0 ? series[series.length - 1] : null;

  // The series already carries the budget that was in effect for each charted
  // period — not today's amount — so a mid-year raise doesn't retroactively
  // rewrite history. Falls back to the current amount when nothing is charted.
  const budget = latest ? Math.abs(latest.budget) : Math.abs(group.value);

  const actual =
    latest && Number.isFinite(latest.actual) ? latest.actual : null;

  // Before the budget existed there is no target, so no status and no
  // variance: its zero budget read every dollar as "Above target" in red over
  // an all-grey chart (w21/101).
  const firstBudget = firstBudgetDate(group.budgetHistory);
  if (latest && beforeFirstBudget(latest, firstBudget, today)) {
    return {
      budget,
      actual,
      variance: null,
      status: null,
      favorable: true,
      progressPercent: null,
      startsOn: firstBudget,
    };
  }

  const variance = actual === null ? null : actual - budget;
  const status =
    variance === null
      ? null
      : varianceStatus(variance, budgetScale(group.budgetHistory));
  const favorable =
    status === null ? true : isFavorableVariance(status, direction);
  const progressPercent =
    actual === null || budget <= 0
      ? null
      : Math.max(0, (actual / budget) * 100);

  return {
    budget,
    actual,
    variance,
    status,
    favorable,
    progressPercent,
    startsOn: null,
  };
}
