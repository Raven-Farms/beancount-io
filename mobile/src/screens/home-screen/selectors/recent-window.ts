/**
 * Home's Recent Transactions shows what has happened: entries dated up to and
 * including today. The journal sorts newest first with no cap at today, so
 * entries pre-entered for later (rent for the next five months, forecast or
 * amortize copies) filled all five rows and hid what had actually happened
 * (w21/471).
 *
 * The query asks through the end of the month and a few more rows than the card
 * shows, and `recentTransactionsUpTo` drops the future ones on the client. A
 * window ending today changed the query's variables, and so its cache key,
 * every day: the copy persisted for offline use had no entry the next morning
 * and the card read "Couldn't load" (w21/513). The range needs both ends, so
 * it starts at the earliest date the ledger accepts.
 */
export function recentTransactionsWindow(today: string): string {
  const year = Number(today.slice(0, 4));
  const month = Number(today.slice(5, 7));
  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return `0001-01-01 - ${today.slice(0, 8)}${String(lastDay).padStart(2, "0")}`;
}

/** Rows asked for beyond the card's own, to absorb entries dated later this month. */
export const RECENT_FUTURE_BUFFER = 20;

/** The newest `limit` entries dated no later than `today`. */
export function recentTransactionsUpTo<T extends { date: string }>(
  entries: readonly T[],
  today: string,
  limit: number,
): T[] {
  return entries.filter((entry) => entry.date <= today).slice(0, limit);
}
