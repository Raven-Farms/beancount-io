import { afterEach, describe, expect, it } from "vitest";
import { enUS } from "date-fns/locale/en-US";
import { fr } from "date-fns/locale/fr";
import { de } from "date-fns/locale/de";
import { ja } from "date-fns/locale/ja";
import { zhCN } from "date-fns/locale/zh-CN";
import {
  ISO_PATTERN,
  calendarToIsoDate,
  formatIsoDate,
  getDisplayPattern,
  getPatternHint,
  parseStrictCalendarDate,
  rollingCalendarBounds,
  isoDateToCalendar,
  todayIsoDate,
} from "../date-picker-utils";

/**
 * One row per tested ordering. `typed` is the locale's own writing of
 * 15 June 2025; assertions pin the resulting date, never just success.
 *
 * NOTE on the milestone text: its example digits are transposed — it says a
 * French user types `12/09/2026` "for 9 December". Under day-first order
 * that string is 12 September (day 12, month 9); the day-first writing of
 * 9 December is `09/12/2026`. The vectors below use the correct digits and
 * additionally pin the milestone's literal string per locale.
 */
const LOCALES = [
  {
    name: "en",
    locale: enUS,
    pattern: "MM/dd/yyyy",
    hint: "MM/DD/YYYY",
    typed: "06/15/2025",
    rollover: "02/30/2025",
    partial: "06/15/202",
  },
  {
    name: "fr",
    locale: fr,
    pattern: "dd/MM/yyyy",
    hint: "DD/MM/YYYY",
    typed: "15/06/2025",
    rollover: "30/02/2025",
    partial: "15/06/202",
  },
  {
    name: "de",
    locale: de,
    pattern: "dd.MM.yyyy",
    hint: "DD.MM.YYYY",
    typed: "15.06.2025",
    rollover: "30.02.2025",
    partial: "15.06.202",
  },
  {
    name: "ja",
    locale: ja,
    pattern: "yyyy/MM/dd",
    hint: "YYYY/MM/DD",
    typed: "2025/06/15",
    rollover: "2025/02/30",
    partial: "2025/06/1",
  },
  {
    name: "zh",
    locale: zhCN,
    pattern: "yyyy-MM-dd",
    hint: "YYYY-MM-DD",
    typed: "2025-06-15",
    rollover: "2025-02-30",
    partial: "2025-06-1",
  },
] as const;

describe("getDisplayPattern", () => {
  it.each(LOCALES)("derives $pattern for $name", ({ locale, pattern }) => {
    expect(getDisplayPattern(locale)).toBe(pattern);
  });

  it("widens single-letter years so short years cannot round-trip", () => {
    // fr ships "dd/MM/y" and zh ships "yy-MM-dd" from date-fns; both must
    // come out requiring a full year.
    expect(getDisplayPattern(fr)).toBe("dd/MM/yyyy");
    expect(getDisplayPattern(zhCN)).toBe("yyyy-MM-dd");
  });

  it("derives hints that cannot drift from the parser", () => {
    for (const { pattern, hint } of LOCALES) {
      expect(getPatternHint(pattern)).toBe(hint);
    }
    expect(getPatternHint(ISO_PATTERN)).toBe("YYYY-MM-DD");
  });
});

describe("parseStrictCalendarDate", () => {
  it.each(LOCALES)(
    "reads $name input in $name order: $typed is 15 June 2025",
    ({ pattern, typed }) => {
      expect(parseStrictCalendarDate(typed, pattern)).toBe("2025-06-15");
    },
  );

  it.each(LOCALES)("accepts the ISO fallback under $name", ({ pattern }) => {
    expect(parseStrictCalendarDate("2025-06-15", pattern)).toBe("2025-06-15");
  });

  it("reads the milestone string per-locale instead of guessing", () => {
    // The milestone's literal `12/09/2026`: 9 December in month-first
    // English, 12 September in day-first French. Each locale applies only
    // its own pattern; neither reinterpretation is attempted.
    expect(parseStrictCalendarDate("12/09/2026", "MM/dd/yyyy")).toBe(
      "2026-12-09",
    );
    expect(parseStrictCalendarDate("12/09/2026", "dd/MM/yyyy")).toBe(
      "2026-09-12",
    );
  });

  it("produces 9 December from the French writing of 9 December", () => {
    expect(parseStrictCalendarDate("09/12/2026", "dd/MM/yyyy")).toBe(
      "2026-12-09",
    );
  });

  it.each(LOCALES)(
    "rejects empty, partial, invalid and rolled-over $name input (m24)",
    ({ pattern, rollover, partial }) => {
      expect(parseStrictCalendarDate("", pattern)).toBeUndefined();
      expect(parseStrictCalendarDate("0", pattern)).toBeUndefined();
      expect(parseStrictCalendarDate(partial, pattern)).toBeUndefined();
      expect(parseStrictCalendarDate("not-a-date", pattern)).toBeUndefined();
      expect(parseStrictCalendarDate(rollover, pattern)).toBeUndefined();
    },
  );

  it.each(LOCALES)("rejects two-digit years under $name", ({ pattern }) => {
    const shortYear = pattern
      .replace("yyyy", "YY")
      .replace("MM", "06")
      .replace("dd", "15")
      .replace("YY", "25");
    expect(parseStrictCalendarDate(shortYear, pattern)).toBeUndefined();
  });

  it("rejects input valid only under another locale ordering", () => {
    // Day-first strings under English, month-first strings under French:
    // legitimate dates elsewhere, invalid here — refused, never reinterpreted.
    expect(parseStrictCalendarDate("15/06/2025", "MM/dd/yyyy")).toBeUndefined();
    expect(parseStrictCalendarDate("06/15/2025", "dd/MM/yyyy")).toBeUndefined();
    expect(parseStrictCalendarDate("15.06.2025", "MM/dd/yyyy")).toBeUndefined();
    expect(parseStrictCalendarDate("06/15/2025", "dd.MM.yyyy")).toBeUndefined();
    expect(parseStrictCalendarDate("2025/06/15", "MM/dd/yyyy")).toBeUndefined();
  });

  it("accepts surrounding whitespace exactly like the bare input", () => {
    expect(parseStrictCalendarDate("  06/15/2025  ", "MM/dd/yyyy")).toBe(
      "2025-06-15",
    );
    expect(parseStrictCalendarDate("  15/06/2025  ", "dd/MM/yyyy")).toBe(
      "2025-06-15",
    );
  });
});

describe("rollingCalendarBounds", () => {
  // A ledger year is 0001–9999: no year 0, negative or five-digit choice
  // reaches the calendar's dropdown (w4/326).
  it.each([
    ["0001-01-01", "0001-01-01", "0101-12-31"],
    ["0050-06-15", "0001-01-01", "0150-12-31"],
    ["9999-12-31", "9899-01-01", "9999-12-31"],
  ])("keeps the years around %s inside 0001–9999", (anchor, start, end) => {
    const { startMonth, endMonth } = rollingCalendarBounds(
      isoDateToCalendar(anchor),
    );
    expect(calendarToIsoDate(startMonth)).toBe(start);
    expect(calendarToIsoDate(endMonth)).toBe(end);
  });

  it("spans 100 years before and after the anchor year", () => {
    const { startMonth, endMonth } = rollingCalendarBounds(
      isoDateToCalendar("2026-12-01"),
    );
    expect(calendarToIsoDate(startMonth)).toBe("1926-01-01");
    expect(calendarToIsoDate(endMonth)).toBe("2126-12-31");
  });

  it("rolls when the displayed month moves into a future year", () => {
    const { startMonth, endMonth } = rollingCalendarBounds(
      isoDateToCalendar("2027-01-01"),
    );
    expect(calendarToIsoDate(startMonth)).toBe("1927-01-01");
    expect(calendarToIsoDate(endMonth)).toBe("2127-12-31");
  });
});

/**
 * Pacific/Apia skipped 2011-12-30 entirely, so a local Date for that day
 * normalizes to the 31st. The civil-day contract must not depend on it (m32).
 */
describe.each(["UTC", "Pacific/Apia", "America/Los_Angeles"])(
  "civil days under TZ=%s",
  (zone) => {
    const originalTz = process.env.TZ;
    afterEach(() => {
      process.env.TZ = originalTz;
    });
    const inZone = () => {
      process.env.TZ = zone;
    };

    it("keeps 2011-12-29, 30 and 31 exact in ISO and display order", () => {
      inZone();
      for (const day of ["29", "30", "31"]) {
        expect(parseStrictCalendarDate(`2011-12-${day}`, "MM/dd/yyyy")).toBe(
          `2011-12-${day}`,
        );
        expect(parseStrictCalendarDate(`12/${day}/2011`, "MM/dd/yyyy")).toBe(
          `2011-12-${day}`,
        );
        expect(formatIsoDate(`2011-12-${day}`, "MM/dd/yyyy")).toBe(
          `12/${day}/2011`,
        );
        expect(calendarToIsoDate(isoDateToCalendar(`2011-12-${day}`))).toBe(
          `2011-12-${day}`,
        );
      }
    });

    it("still refuses impossible days and accepts leap days", () => {
      inZone();
      expect(
        parseStrictCalendarDate("2011-02-29", "MM/dd/yyyy"),
      ).toBeUndefined();
      expect(
        parseStrictCalendarDate("2011-12-32", "MM/dd/yyyy"),
      ).toBeUndefined();
      expect(parseStrictCalendarDate("2012-02-29", "MM/dd/yyyy")).toBe(
        "2012-02-29",
      );
    });

    it("reads Today from the local clock", () => {
      inZone();
      const now = new Date();
      const local = [
        String(now.getFullYear()).padStart(4, "0"),
        String(now.getMonth() + 1).padStart(2, "0"),
        String(now.getDate()).padStart(2, "0"),
      ].join("-");
      expect(todayIsoDate()).toBe(local);
    });
  },
);

it("reproduces the Apia skipped day the civil contract guards against", () => {
  const originalTz = process.env.TZ;
  process.env.TZ = "Pacific/Apia";
  try {
    // A local-midnight Date for the 30th rolls to the 31st in this zone.
    expect(new Date(2011, 11, 30).getDate()).toBe(31);
  } finally {
    process.env.TZ = originalTz;
  }
});

/** Gregorian dates typed with Persian or Arabic-Indic digits (w4/325). */
describe("parseStrictCalendarDate with localized digits", () => {
  it.each([
    ["Persian", "۲۰۲۶/۱۰/۲۲"],
    ["Arabic-Indic", "٢٠٢٦/١٠/٢٢"],
    ["mixed", "۲۰26/١٠/22"],
  ])("reads %s digits as the same Gregorian day", (_name, typed) => {
    expect(parseStrictCalendarDate(typed, "yyyy/MM/dd")).toBe("2026-10-22");
  });

  it("reads the ISO fallback in Persian digits", () => {
    expect(parseStrictCalendarDate("۲۰۲۶-۱۰-۲۲", "yyyy/MM/dd")).toBe(
      "2026-10-22",
    );
  });

  it.each([
    ["an impossible month", "۲۰۲۶/۱۳/۲۲"],
    ["a February 30", "٢٠٢٦/٠٢/٣٠"],
    ["a partial date", "۲۰۲۶/۱۰"],
    ["a two-digit year", "۲۶/۱۰/۲۲"],
  ])("still refuses %s", (_name, typed) => {
    expect(parseStrictCalendarDate(typed, "yyyy/MM/dd")).toBeUndefined();
  });
});
