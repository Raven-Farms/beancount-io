/**
 * Calendar dates built without JavaScript's two-digit-year rule (w21/043).
 *
 * `Date.UTC(year, …)` and `new Date(year, …)` read a year of 0–99 as
 * 1900–1999, so a ledger entry dated `0050-03-01` — which the ledger accepts —
 * displayed as March 1, 1950 and shifted every period computed from it.
 * `setUTCFullYear`/`setFullYear` take the year as given. Month and day overflow
 * the way `Date.UTC` does (day 0 is the previous month's last day).
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */

/** Epoch ms at UTC midnight of the given calendar day. */
export function utcTime(year: number, monthIndex: number, day: number): number {
  const date = new Date(0);
  date.setUTCFullYear(year, monthIndex, day);
  return date.getTime();
}

/** UTC midnight of the given calendar day. */
export function utcDate(year: number, monthIndex: number, day: number): Date {
  return new Date(utcTime(year, monthIndex, day));
}

/** Local midnight of the given calendar day. */
export function localDate(year: number, monthIndex: number, day: number): Date {
  const date = new Date(2000, 0, 1);
  date.setFullYear(year, monthIndex, day);
  return date;
}
