export const getFormatDate = (date: Date) => {
  // Four digits, as a ledger date needs for years before 1000 (w21/043).
  // An invalid date still reads NaN-NaN-NaN rather than 0NaN.
  const fullYear = date.getFullYear();
  const year = Number.isNaN(fullYear)
    ? String(fullYear)
    : String(fullYear).padStart(4, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

/**
 * Inverse of `getFormatDate`: a ledger `YYYY-MM-DD` as local midnight.
 *
 * `new Date("YYYY-MM-DD")` is UTC midnight and shifts the calendar day west
 * of Greenwich — the same trap documented for `formatLedgerDate`. Append
 * `T00:00:00` so the date picker and `getFormatDate` round-trip on the day
 * the ledger string named.
 */
export function parseFormatDate(isoDate: string): Date {
  return new Date(`${isoDate}T00:00:00`);
}
