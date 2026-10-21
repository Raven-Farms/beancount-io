/**
 * Pure recurrence detector: a per-payee series of (date, currency, amount) →
 * a cadence verdict, or null when the series is too short or too irregular.
 *
 * "Today" is an explicit parameter — never read the clock here — so tests can
 * pin the overdue boundary without flaking. Free of `@/` value imports so the
 * jest-lite runner can require it.
 */
import { utcDate, utcTime } from "../../../common/calendar-date";

export type Cadence =
  "weekly" | "biweekly" | "monthly" | "quarterly" | "yearly";

/** One posting event feeding detection. Dates are ledger `YYYY-MM-DD`. */
export interface SeriesPoint {
  date: string;
  currency: string;
  amount: number;
}

export interface RecurrenceVerdict {
  cadence: Cadence;
  /** Median amount per currency (signed as in the series). */
  typicalAmountByCurrency: Record<string, number>;
  /** True when any currency's amount spread exceeds ~10% of its median. */
  isApproximate: boolean;
  /**
   * The next event as `YYYY-MM-DD`: for a bill kept on one day of the month,
   * that day in the next period's month; otherwise last event + median gap.
   */
  nextExpected: string;
  /** True when `today` is past `nextExpected` by more than the grace window. */
  isOverdue: boolean;
  /**
   * The earliest pre-entered event after today, `YYYY-MM-DD`. It is the
   * upcoming occurrence, not a payment made: counted as paid, a pre-entered
   * rent cheque hid the missed month before it (w21/167).
   */
  scheduled?: string;
}

/** Minimum distinct event dates before a cadence can be inferred. */
const MIN_EVENT_DATES = 3;

/** Accept a median gap only when MAD/median stays under this. */
const MAX_GAP_DISPERSION = 0.25;

/** Flag typical amount as approximate when (max−min)/|median| exceeds this. */
const APPROXIMATE_AMOUNT_SPREAD = 0.1;

/** Overdue grace as a fraction of the median gap. */
const OVERDUE_GRACE_FRACTION = 0.25;

const MS_PER_DAY = 86_400_000;

/**
 * Cadence bands in whole days. Monthly covers month-length wobble (27–32);
 * every-4-weeks lands in the same band as monthly by design.
 */
const CADENCE_BANDS: ReadonlyArray<{
  cadence: Cadence;
  min: number;
  max: number;
}> = [
  { cadence: "weekly", min: 6, max: 8 },
  { cadence: "biweekly", min: 13, max: 16 },
  { cadence: "monthly", min: 27, max: 32 },
  { cadence: "quarterly", min: 84, max: 98 },
  { cadence: "yearly", min: 350, max: 380 },
];

/**
 * Parse a ledger date as a timezone-free day number (UTC midnight epoch days).
 * Invalid or non-`YYYY-MM-DD` strings return null — never throw.
 */
export function parseLedgerDay(date: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date.trim());
  if (!match) {
    return null;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const ms = utcTime(year, month - 1, day);
  if (!Number.isFinite(ms)) {
    return null;
  }
  const probe = new Date(ms);
  if (
    probe.getUTCFullYear() !== year ||
    probe.getUTCMonth() !== month - 1 ||
    probe.getUTCDate() !== day
  ) {
    return null;
  }
  return Math.floor(ms / MS_PER_DAY);
}

/** Format an epoch-day number back to `YYYY-MM-DD` (UTC). */
export function formatLedgerDay(dayNumber: number): string {
  const ms = dayNumber * MS_PER_DAY;
  const date = new Date(ms);
  // Four digits, as a ledger writes 0050 (w21/043).
  const year = String(date.getUTCFullYear()).padStart(4, "0");
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** Calendar months a monthly, quarterly or yearly bill advances by. */
const CADENCE_MONTHS: Partial<Record<Cadence, number>> = {
  monthly: 1,
  quarterly: 3,
  yearly: 12,
};

type CalendarDay = { year: number; month: number; day: number };

function calendarDay(dayNumber: number): CalendarDay {
  const date = new Date(dayNumber * MS_PER_DAY);
  return {
    year: date.getUTCFullYear(),
    month: date.getUTCMonth(),
    day: date.getUTCDate(),
  };
}

function daysInMonth(year: number, month: number): number {
  return utcDate(year, month + 1, 0).getUTCDate();
}

/** `months` calendar months after `dayNumber`, on day `anchor` clamped to the month. */
function addMonthsClamped(
  dayNumber: number,
  months: number,
  anchor = calendarDay(dayNumber).day,
): number {
  const { year, month } = calendarDay(dayNumber);
  const target = utcDate(year, month + months, 1);
  const lastDay = daysInMonth(target.getUTCFullYear(), target.getUTCMonth());
  return (
    Math.floor(target.getTime() / MS_PER_DAY) + Math.min(anchor, lastDay) - 1
  );
}

/**
 * The day of the month a series is kept on, or null when it is not: every
 * event falls on that day (clamped at a short month's end, so a 31st bill
 * paid on 30 Jun still counts) and each is `months` after the one before.
 * Every-four-weeks payments share the monthly gap band but drift through the
 * month, so they keep the day-count step (w21/007).
 */
function monthDayAnchor(
  eventDays: readonly number[],
  months: number,
): number | null {
  const days = eventDays.map(calendarDay);
  const anchor = Math.max(...days.map((d) => d.day));
  const kept = days.every(
    (d, i) =>
      d.day === Math.min(anchor, daysInMonth(d.year, d.month)) &&
      (i === 0 ||
        (d.year - days[i - 1]!.year) * 12 + d.month - days[i - 1]!.month ===
          months),
  );
  return kept ? anchor : null;
}

function sortedCopy(values: readonly number[]): number[] {
  return [...values].sort((a, b) => a - b);
}

/** Median of a non-empty numeric list. Even length → mean of the two middle. */
export function median(values: readonly number[]): number | null {
  if (values.length === 0) {
    return null;
  }
  const sorted = sortedCopy(values);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1]! + sorted[mid]!) / 2;
  }
  return sorted[mid]!;
}

/** Median absolute deviation from `center`. */
function mad(values: readonly number[], center: number): number {
  return median(values.map((value) => Math.abs(value - center))) ?? 0;
}

function classifyCadence(medianGap: number): Cadence | null {
  for (const band of CADENCE_BANDS) {
    if (medianGap >= band.min && medianGap <= band.max) {
      return band.cadence;
    }
  }
  return null;
}

function amountSpreadIsApproximate(amounts: readonly number[]): boolean {
  if (amounts.length === 0) {
    return false;
  }
  const med = median(amounts);
  if (med === null) {
    return false;
  }
  const sorted = sortedCopy(amounts);
  const min = sorted[0]!;
  const max = sorted[sorted.length - 1]!;
  const spread = max - min;
  if (spread === 0) {
    return false;
  }
  const scale = Math.abs(med);
  if (scale === 0) {
    return true;
  }
  return spread / scale > APPROXIMATE_AMOUNT_SPREAD;
}

/**
 * Whether `series` has enough distinct, valid event dates for a cadence to be
 * inferred at all. A null `detectRecurrence` means "too short" when this is
 * false and "analysed, no steady pattern" when it is true; a manual Recurring
 * mark reads the difference (w0/039).
 */
export function hasEnoughHistory(series: readonly SeriesPoint[]): boolean {
  const days = new Set<number>();
  for (const point of series) {
    const day = parseLedgerDay(point.date);
    if (day !== null && Number.isFinite(point.amount)) {
      days.add(day);
    }
  }
  return days.size >= MIN_EVENT_DATES;
}

/**
 * Detect a steady cadence in `series`.
 *
 * Same-day duplicates collapse for gap math (a 0-day gap must not poison the
 * median) but still contribute to per-currency amount medians. Returns null
 * for short, unclassifiable, or high-dispersion series.
 */
export function detectRecurrence(
  series: readonly SeriesPoint[],
  today: string,
): RecurrenceVerdict | null {
  if (series.length < MIN_EVENT_DATES) {
    return null;
  }

  const todayDay = parseLedgerDay(today);
  if (todayDay === null) {
    return null;
  }

  // Only what has happened says how often it happens, when it last did, and
  // whether it is late; a pre-entered future event is the next one (w21/167).
  const byDay = new Map<number, SeriesPoint[]>();
  let scheduledDay: number | null = null;
  for (const point of series) {
    const day = parseLedgerDay(point.date);
    if (day === null || !Number.isFinite(point.amount)) {
      continue;
    }
    if (day > todayDay) {
      if (scheduledDay === null || day < scheduledDay) scheduledDay = day;
      continue;
    }
    const bucket = byDay.get(day);
    if (bucket) {
      bucket.push(point);
    } else {
      byDay.set(day, [point]);
    }
  }

  const eventDays = [...byDay.keys()].sort((a, b) => a - b);
  if (eventDays.length < MIN_EVENT_DATES) {
    return null;
  }

  const gaps: number[] = [];
  for (let i = 1; i < eventDays.length; i++) {
    gaps.push(eventDays[i]! - eventDays[i - 1]!);
  }

  const medianGap = median(gaps);
  if (medianGap === null || medianGap <= 0) {
    return null;
  }

  const dispersion = mad(gaps, medianGap) / medianGap;
  if (dispersion >= MAX_GAP_DISPERSION) {
    return null;
  }

  const cadence = classifyCadence(medianGap);
  if (!cadence) {
    return null;
  }

  const amountsByCurrency = new Map<string, number[]>();
  for (const points of byDay.values()) {
    for (const point of points) {
      const currency = point.currency.trim();
      if (!currency) {
        continue;
      }
      const list = amountsByCurrency.get(currency);
      if (list) {
        list.push(point.amount);
      } else {
        amountsByCurrency.set(currency, [point.amount]);
      }
    }
  }

  if (amountsByCurrency.size === 0) {
    return null;
  }

  const typicalAmountByCurrency: Record<string, number> = {};
  let isApproximate = false;
  for (const [currency, amounts] of amountsByCurrency) {
    const med = median(amounts);
    if (med === null) {
      continue;
    }
    typicalAmountByCurrency[currency] = med;
    if (amountSpreadIsApproximate(amounts)) {
      isApproximate = true;
    }
  }

  if (Object.keys(typicalAmountByCurrency).length === 0) {
    return null;
  }

  const gapDays = Math.round(medianGap);
  const lastDay = eventDays[eventDays.length - 1]!;
  // A bill kept on one day of the month is due that day: the median of
  // 28–31-day gaps rounds to 31 and used to land one to three days late.
  const months = CADENCE_MONTHS[cadence];
  const anchor =
    months === undefined ? null : monthDayAnchor(eventDays, months);
  const nextExpectedDay =
    months !== undefined && anchor !== null
      ? addMonthsClamped(lastDay, months, anchor)
      : lastDay + gapDays;
  const graceDays = Math.max(1, Math.round(gapDays * OVERDUE_GRACE_FRACTION));
  const isOverdue = todayDay > nextExpectedDay + graceDays;

  return {
    cadence,
    typicalAmountByCurrency,
    isApproximate,
    nextExpected: formatLedgerDay(nextExpectedDay),
    isOverdue,
    ...(scheduledDay === null
      ? {}
      : { scheduled: formatLedgerDay(scheduledDay) }),
  };
}
