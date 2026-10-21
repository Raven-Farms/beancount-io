import { localDate } from "../../common/calendar-date";

/**
 * The open date Open Account starts on. Reached from a dated entry form, the
 * account opens on that entry's date, so a back-dated receipt with a new
 * category saves in one pass instead of being refused because the account
 * "was not opened until" today (w21/008). A route param can come from any
 * deep link, so anything malformed, impossible or after today falls back to
 * today, and the field stays editable either way.
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */
export function initialOpenDate(param: string | undefined, now: Date): Date {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(param ?? "");
  if (!match) return now;
  const [year, month, day] = match.slice(1).map(Number);
  // Local midnight, as `parseFormatDate` reads a ledger date.
  const date = localDate(year!, month! - 1, day!);
  const real =
    date.getFullYear() === year &&
    date.getMonth() === month! - 1 &&
    date.getDate() === day;
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return real && date <= today ? date : now;
}
