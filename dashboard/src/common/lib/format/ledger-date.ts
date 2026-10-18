/**
 * A formatter for ledger dates in the reader's language, always on the
 * Gregorian calendar. Ledger dates are Gregorian (the file, the Journal, the
 * period tables, CSV and the date picker all say `2026-08-28`), but
 * `Intl.DateTimeFormat("fa")` defaults to the Solar Hijri calendar, which
 * titled August 2026's figures "شهریور ۱۴۰۵" — a month they are not. Month
 * names and numerals still follow the language ("اوت ۲۰۲۶").
 *
 * Instants that are not ledger dates (commit times, sign-up dates) may keep
 * the locale's own calendar.
 */
export function ledgerDateFormat(
  language: string,
  options: Intl.DateTimeFormatOptions,
): Intl.DateTimeFormat {
  return new Intl.DateTimeFormat(language, { ...options, calendar: "gregory" });
}
