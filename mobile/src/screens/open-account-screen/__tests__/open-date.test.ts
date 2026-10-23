import { initialOpenDate } from "../open-date";

// Open Account reached from a back-dated New Transaction opens on the entry's
// date, so the transaction is not refused for an account "not opened until"
// today (w21/008). Anything a deep link could smuggle in falls back to today.
const NOW = new Date(2026, 9, 20, 14, 30);
const ymd = (date: Date) =>
  [date.getFullYear(), date.getMonth() + 1, date.getDate()].join("-");

describe("initialOpenDate", () => {
  it("opens on the entry's date when it is in the past", () => {
    expect(ymd(initialOpenDate("2026-08-25", NOW))).toBe("2026-8-25");
  });

  it("accepts today", () => {
    expect(ymd(initialOpenDate("2026-10-20", NOW))).toBe("2026-10-20");
  });

  it("keeps today for a future entry", () => {
    expect(initialOpenDate("2026-10-21", NOW)).toBe(NOW);
  });

  it("keeps today with no date or a malformed one", () => {
    for (const param of [
      undefined,
      "",
      "2026-8-25",
      "yesterday",
      "2026-02-30",
    ]) {
      expect(initialOpenDate(param, NOW)).toBe(NOW);
    }
  });
});
