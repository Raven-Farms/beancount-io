import { format, isValid, parse, type Locale as DateFnsLocale } from "date-fns";
import type { DateLib } from "react-day-picker";

/** Always-accepted fallback, in every language. */
export const ISO_PATTERN = "yyyy-MM-dd";

/** Used when a locale exposes no short date pattern; the en-US short pattern. */
const FALLBACK_PATTERN = "MM/dd/yyyy";

/** Years before/after the displayed month for DayPicker dropdown navigation. */
const DROPDOWN_YEAR_SPAN = 100;

/**
 * A Date whose calendar fields read and write UTC. Parsing and formatting a
 * ledger date through it keeps the civil day exact even when the browser
 * timezone never had that local midnight — Pacific/Apia skipped 2011-12-30,
 * so a local Date for it silently becomes the 31st (w4/m32). date-fns builds
 * every intermediate value from this class via `constructor`.
 */
class CivilDate extends Date {
  getFullYear() {
    return this.getUTCFullYear();
  }
  getMonth() {
    return this.getUTCMonth();
  }
  getDate() {
    return this.getUTCDate();
  }
  getDay() {
    return this.getUTCDay();
  }
  getHours() {
    return this.getUTCHours();
  }
  getMinutes() {
    return this.getUTCMinutes();
  }
  getSeconds() {
    return this.getUTCSeconds();
  }
  getMilliseconds() {
    return this.getUTCMilliseconds();
  }
  getTimezoneOffset() {
    return 0;
  }
  toLocaleDateString(
    locales?: Intl.LocalesArgument,
    options?: Intl.DateTimeFormatOptions,
  ) {
    return super.toLocaleDateString(locales, { ...options, timeZone: "UTC" });
  }
  setFullYear(...args: Parameters<Date["setUTCFullYear"]>) {
    return this.setUTCFullYear(...args);
  }
  setMonth(...args: Parameters<Date["setUTCMonth"]>) {
    return this.setUTCMonth(...args);
  }
  setDate(...args: Parameters<Date["setUTCDate"]>) {
    return this.setUTCDate(...args);
  }
  setHours(...args: Parameters<Date["setUTCHours"]>) {
    return this.setUTCHours(...args);
  }
  setMinutes(...args: Parameters<Date["setUTCMinutes"]>) {
    return this.setUTCMinutes(...args);
  }
  setSeconds(...args: Parameters<Date["setUTCSeconds"]>) {
    return this.setUTCSeconds(...args);
  }
  setMilliseconds(...args: Parameters<Date["setUTCMilliseconds"]>) {
    return this.setUTCMilliseconds(...args);
  }
}

/** Today's civil day in the browser's own timezone, as `yyyy-MM-dd`. */
export function todayIsoDate(): string {
  return format(new Date(), ISO_PATTERN);
}

function civilDay(year: number, monthIndex: number, day: number): Date {
  const date = new CivilDate(0);
  date.setFullYear(year, monthIndex, day);
  return date;
}

/**
 * The calendar's dates are CivilDates too, so a civil day maps to its UTC
 * midnight there and back — never to a local midnight that may not exist.
 */
export function isoDateToCalendar(isoDate: string): Date {
  return parse(isoDate, ISO_PATTERN, new CivilDate(0));
}

/**
 * DayPicker date factories that keep its whole grid on CivilDates; date-fns
 * arithmetic preserves the class. Its own `timeZone="UTC"` mode does not
 * help: TZDate mirrors wall time through the system zone, so Apia still
 * loses 2011-12-30.
 */
export const civilCalendarDateLib: Partial<DateLib> = {
  today: calendarToday,
  newDate: civilDay,
};

/** Today's local civil day as a calendar value. */
export function calendarToday(): Date {
  return isoDateToCalendar(todayIsoDate());
}

/** The civil day of a date the calendar handed back. */
export function calendarToIsoDate(date: Date): string {
  return format(new CivilDate(date.getTime()), ISO_PATTERN);
}

/** A canonical `yyyy-MM-dd` day rendered in a display pattern. */
export function formatIsoDate(
  isoDate: string | undefined,
  pattern: string,
  locale?: DateFnsLocale,
): string {
  if (!isoDate) return "";
  const date = isoDateToCalendar(isoDate);
  return isValid(date) ? format(date, pattern, { locale }) : "";
}

/**
 * Rolling start/end months so the year dropdown is not clamped to "today's year".
 * Recompute from the displayed month so browsing past a bound does not freeze the range.
 * `anchor` is a calendar (CivilDate) value, so the bounds are too.
 */
export function rollingCalendarBounds(anchor: Date): {
  startMonth: Date;
  endMonth: Date;
} {
  const year = anchor.getFullYear();
  return {
    startMonth: civilDay(year - DROPDOWN_YEAR_SPAN, 0, 1),
    endMonth: civilDay(year + DROPDOWN_YEAR_SPAN, 11, 31),
  };
}

/**
 * Short numeric date pattern for the active app language — "MM/dd/yyyy" for
 * English, "dd/MM/yyyy" for French, "dd.MM.yyyy" for German, and so on.
 * Order and separators come from the locale's own short date format; any
 * year run is widened to yyyy so a two-digit year can never round-trip —
 * a ledger date needs a full year, and m24 forbids partial-input expansion.
 */
export function getDisplayPattern(locale: DateFnsLocale): string {
  const raw = locale.formatLong.date({ width: "short" });
  return widenYearToken(raw || FALLBACK_PATTERN);
}

/**
 * Uppercase rendering of a pattern for use as an input hint, e.g.
 * "MM/dd/yyyy" becomes "MM/DD/YYYY". Derived from the pattern actually
 * parsed so the hint cannot drift from the parser.
 */
export function getPatternHint(pattern: string): string {
  return pattern.toUpperCase();
}

/** Replace every unquoted y-run with yyyy; quoted literals pass through. */
function widenYearToken(pattern: string): string {
  let out = "";
  let i = 0;
  while (i < pattern.length) {
    const ch = pattern[i];
    if (ch === "'") {
      // Copy the quoted literal verbatim; '' is an escaped quote.
      out += ch;
      i += 1;
      while (i < pattern.length) {
        out += pattern[i];
        if (pattern[i] === "'") {
          if (pattern[i + 1] === "'") {
            out += pattern[i + 1];
            i += 2;
            continue;
          }
          i += 1;
          break;
        }
        i += 1;
      }
      continue;
    }
    if (ch === "y") {
      while (i < pattern.length && pattern[i] === "y") i += 1;
      out += "yyyy";
      continue;
    }
    out += ch;
    i += 1;
  }
  return out;
}

/**
 * Arabic-Indic (U+0660–0669) and Persian (U+06F0–06F9) decimal digits as
 * ASCII, so a Gregorian date typed in a Persian or Arabic layout reads the
 * same as its ASCII writing (w4/325). Each block's low nibble is its value;
 * nothing else is treated as a digit.
 */
function asciiDigits(text: string): string {
  return text.replace(/[\u0660-\u0669\u06F0-\u06F9]/g, (digit) =>
    String(digit.charCodeAt(0) & 0xf),
  );
}

/**
 * Strict calendar-date parse under exactly one locale pattern plus the ISO
 * fallback; rejects partial text and month-length rollover. Never tries
 * several orderings: input matching neither pattern is invalid, so a
 * day-first string under a month-first language (or vice versa) is refused
 * rather than silently reinterpreted. Returns the canonical `yyyy-MM-dd`
 * civil day, independent of the browser timezone.
 */
export function parseStrictCalendarDate(
  input: string,
  displayPattern: string,
): string | undefined {
  const trimmed = asciiDigits(input.trim());
  if (!trimmed) return undefined;

  for (const pattern of [displayPattern, ISO_PATTERN]) {
    const parsed = parse(trimmed, pattern, new CivilDate(0));
    if (isValid(parsed) && format(parsed, pattern) === trimmed) {
      return format(parsed, ISO_PATTERN);
    }
  }
  return undefined;
}
