import { resolveCurrencyBalance } from "../../../common/balance-util";
import { notInTotalOf, type Holding } from "../../../common/balance-display";
import { formatMoneyWithCurrency } from "../../../common/number-utils";
import { formatTimeFilter } from "../../transactions-screen/filters/select-filter-query";

export type SpendingCompare = {
  thisMonth: number;
  lastMonth: number;
  /**
   * Spending over the two months in other currencies, which the bars cannot
   * include: the card used to read "This month $0" over a 50 EUR expense with
   * no hint (w21/038).
   */
  notInTotal: Holding[];
  thisMonthKey: string;
  lastMonthKey: string;
};

/** One month of the Expenses root's activity, as `getLedgerIntervalTotals` returns it. */
export type MonthTotal = {
  /** A date inside the month. */
  date: string;
  balance: Record<string, number | string> | null | undefined;
};

/** Format a year + 1-based month as a "YYYY-MM" key. */
function toMonthKey(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, "0")}`;
}

function monthKeys(referenceDate: Date) {
  const year = referenceDate.getFullYear();
  const month = referenceDate.getMonth() + 1; // 1-based
  return {
    thisMonthKey: toMonthKey(year, month),
    lastMonthKey:
      month === 1 ? toMonthKey(year - 1, 12) : toMonthKey(year, month - 1),
  };
}

/**
 * The `time` window the card asks for: the first of last month through the end
 * of this one. Both months come back whole however many transactions they
 * hold (w21/011). The window is the same all month: ending it on today made
 * a new cache key every day, so the next day offline found yesterday's result
 * unreadable and the card failed to load (w21/184).
 */
export function spendingWindow(referenceDate: Date = new Date()): string {
  const { lastMonthKey, thisMonthKey } = monthKeys(referenceDate);
  const lastDay = new Date(
    referenceDate.getFullYear(),
    referenceDate.getMonth() + 1,
    0,
  ).getDate();
  return formatTimeFilter({
    start: `${lastMonthKey}-01`,
    end: `${thisMonthKey}-${String(lastDay).padStart(2, "0")}`,
  });
}

/**
 * Spending this month vs. last month in the active currency, from the
 * Expenses root's monthly totals (sub-accounts rolled up server-side). The
 * card used to sum the newest 200 journal rows, so a month with more
 * transactions than that hid last month's spending entirely and capped this
 * month's (w21/011). `referenceDate` is injectable for deterministic tests.
 */
export function selectSpendingCompare(
  months: readonly MonthTotal[],
  currency: string,
  referenceDate: Date = new Date(),
): SpendingCompare {
  const { thisMonthKey, lastMonthKey } = monthKeys(referenceDate);
  let thisMonth = 0;
  let lastMonth = 0;
  const omitted = new Map<string, Holding>();
  for (const month of months) {
    const key = month.date.slice(0, 7);
    if (key !== thisMonthKey && key !== lastMonthKey) continue;
    const spent = resolveCurrencyBalance(month.balance, currency);
    if (key === thisMonthKey) thisMonth += spent;
    else lastMonth += spent;
    for (const holding of notInTotalOf(month.balance, currency)) {
      const prior = omitted.get(holding.currency);
      const scale = Math.max(prior?.scale ?? 0, holding.scale);
      omitted.set(holding.currency, {
        currency: holding.currency,
        scale,
        number: Number(((prior?.number ?? 0) + holding.number).toFixed(scale)),
      });
    }
  }
  const notInTotal = [...omitted.values()].filter(
    (holding) => holding.number !== 0,
  );
  return { thisMonth, lastMonth, notInTotal, thisMonthKey, lastMonthKey };
}

/**
 * The Spending chart as one spoken sentence — both months and their amounts —
 * since its bars and axis ticks are not readable on their own (w21/018).
 */
export function spendingChartSummary(
  { lastMonth, thisMonth }: Pick<SpendingCompare, "lastMonth" | "thisMonth">,
  currency: string,
  t: (key: "spendingChartSummary", params: Record<string, string>) => string,
  /** The card's "Not in total" line, spoken after the amounts (w21/038). */
  note?: string,
): string {
  const summary = t("spendingChartSummary", {
    lastMonth: formatMoneyWithCurrency(lastMonth, currency),
    thisMonth: formatMoneyWithCurrency(thisMonth, currency),
  });
  return note ? `${summary}. ${note}` : summary;
}
