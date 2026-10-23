import { parseISO, isValid, format } from "date-fns";

const CALENDAR_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

/**
 * Format date as ISO YYYY-MM-DD
 * @param dateString - Date string to format
 * @returns Formatted date in YYYY-MM-DD format or null if invalid
 */
export const formatDateISO = (
  dateString: string | null | undefined,
): string | null => {
  if (!dateString) {
    return null;
  }

  // Strip time portion so ISO timestamps are treated as the plain calendar date
  const datePart = dateString.includes("T")
    ? dateString.split("T")[0]
    : dateString;

  // A calendar date is checked in UTC and returned as written: a local
  // midnight the zone skipped (Apia's 2011-12-30) would roll it to the next
  // day (w4/285).
  const calendar = CALENDAR_DATE.exec(datePart);
  if (calendar) {
    const [year, month, day] = calendar.slice(1).map(Number);
    const value = new Date(0);
    value.setUTCFullYear(year, month - 1, day);
    return value.getUTCFullYear() === year &&
      value.getUTCMonth() === month - 1 &&
      value.getUTCDate() === day
      ? datePart
      : null;
  }

  const date = parseISO(datePart);

  if (!isValid(date)) {
    return null;
  }

  return format(date, "yyyy-MM-dd");
};
