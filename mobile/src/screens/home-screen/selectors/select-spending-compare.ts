import { resolveCurrencyBalance } from "../../../common/balance-util";
import { formatMoneyWithCurrency } from "../../../common/number-utils";
import { formatTimeFilter } from "../../transactions-screen/filters/select-filter-query";

export type SpendingCompare = {
  thisMonth: number;
  lastMonth: number;
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
 * The `time` window the card asks for: the first of last month through today.
 * Both months come back whole however many transactions they hold (w21/011).
 */
export function spendingWindow(referenceDate: Date = new Date()): string {
  const { lastMonthKey, thisMonthKey } = monthKeys(referenceDate);
  const day = String(referenceDate.getDate()).padStart(2, "0");
  return formatTimeFilter({
    start: `${lastMonthKey}-01`,
    end: `${thisMonthKey}-${day}`,
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
  for (const month of months) {
    const key = month.date.slice(0, 7);
    const spent = resolveCurrencyBalance(month.balance, currency);
    if (key === thisMonthKey) thisMonth += spent;
    else if (key === lastMonthKey) lastMonth += spent;
  }
  return { thisMonth, lastMonth, thisMonthKey, lastMonthKey };
}

/**
 * The Spending chart as one spoken sentence — both months and their amounts —
 * since its bars and axis ticks are not readable on their own (w21/018).
 */
export function spendingChartSummary(
  { lastMonth, thisMonth }: Pick<SpendingCompare, "lastMonth" | "thisMonth">,
  currency: string,
  t: (key: "spendingChartSummary", params: Record<string, string>) => string,
): string {
  return t("spendingChartSummary", {
    lastMonth: formatMoneyWithCurrency(lastMonth, currency),
    thisMonth: formatMoneyWithCurrency(thisMonth, currency),
  });
}
