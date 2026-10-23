import { localDate } from "../../common/calendar-date";

/**
 * The dates an Update Budget may take. A directive dated before the budget's
 * current one saves, but the newer entry stays in force, so the Update changed
 * nothing and said nothing (w21/623): the date is limited to the current
 * entry's day or later, and starts on today, or on the current entry's day when
 * that is still ahead.
 */
export function updateBudgetDates(
  currentDate: string | undefined,
  today: Date,
): { minimum: Date | undefined; initial: Date } {
  const match = currentDate
    ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(currentDate)
    : null;
  if (!match) return { minimum: undefined, initial: today };
  const minimum = localDate(
    Number(match[1]),
    Number(match[2]) - 1,
    Number(match[3]),
  );
  return { minimum, initial: today < minimum ? minimum : today };
}
