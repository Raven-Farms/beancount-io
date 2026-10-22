import { utcDate } from "../../../common/calendar-date";

/**
 * Home reads this month's spending over a window that holds for the whole
 * month, so its cache key does not change daily and the next day offline still
 * finds the actuals (w21/184). That window also holds the payments pre-entered
 * for later in the month, which are not spent yet: the budget panel read
 * "$400.00 of $338.71, Above target" where the Budget page read $0.00 spent,
 * and Spending's "This month" counted a bill not yet paid (w21/337). The month
 * window stays the default; when the ledger has anything dated after today
 * this month, the in-progress period is read to today instead.
 */

/** The last day of `today`'s month, as `YYYY-MM-DD`. */
function monthEnd(today: string): string {
  const year = Number(today.slice(0, 4));
  const month = Number(today.slice(5, 7));
  const lastDay = utcDate(year, month, 0).getUTCDate();
  return `${today.slice(0, 7)}-${String(lastDay).padStart(2, "0")}`;
}

/** BQL: one row if anything is dated after today and within this month. */
export function scheduledThisMonthBql(today: string): string {
  return `SELECT date WHERE date > ${today} AND date <= ${monthEnd(today)} LIMIT 1`;
}

/** Whether that statement found a row. */
export function hasScheduledRows(
  table: { rows?: readonly unknown[] | null } | null | undefined,
): boolean {
  return Array.isArray(table?.rows) && table.rows.length > 0;
}

/** This month from its first day to today, in the `time` filter's syntax. */
export function monthToDateWindow(today: string): string {
  return `${today.slice(0, 7)}-01 - ${today}`;
}

/**
 * The monthly totals with this month read to today when it has pre-entered
 * entries: last month and earlier come from the month-long window, this month
 * from `monthToDate`. Until that read has landed, this month is left as the
 * window had it.
 */
export function withMonthToDate<T extends { date: string }>(
  months: readonly T[],
  monthToDate: readonly T[] | undefined,
  today: string,
): T[] {
  if (monthToDate === undefined) return [...months];
  const thisMonth = today.slice(0, 7);
  return [
    ...months.filter((month) => month.date.slice(0, 7) !== thisMonth),
    ...monthToDate,
  ];
}
