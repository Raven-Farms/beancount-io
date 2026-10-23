import {
  detectRecurrence,
  hasEnoughHistory,
  type SeriesPoint,
} from "../screens/merchants-screen/selectors/detect-recurrence";

// w21/268: a refund on a bill moved Next, made the amount approximate and could
// stop a short history being detected.
const charge = (date: string): SeriesPoint => ({
  date,
  currency: "USD",
  amount: -11.99,
});
const refund = (date: string): SeriesPoint => ({
  date,
  currency: "USD",
  amount: 11.99,
});
const months = (from: number, to: number) =>
  Array.from({ length: to - from + 1 }, (_, i) =>
    charge(`2026-${String(from + i).padStart(2, "0")}-05`),
  );
const TODAY = "2026-10-21";

describe("a refund does not count as a payment", () => {
  const control = detectRecurrence(months(1, 10), TODAY)!;

  it("matches the charges-only control for a late refund", () => {
    const verdict = detectRecurrence(
      [...months(1, 10), refund("2026-10-09")],
      TODAY,
    )!;
    expect(verdict.nextExpected).toBe(control.nextExpected);
    expect(verdict.isApproximate).toBe(false);
    expect(verdict.typicalAmountByCurrency).toEqual(
      control.typicalAmountByCurrency,
    );
  });

  it("matches the control for a refund mid-history", () => {
    const verdict = detectRecurrence(
      [...months(1, 10), refund("2026-03-09")],
      TODAY,
    )!;
    expect(verdict.nextExpected).toBe(control.nextExpected);
    expect(verdict.isApproximate).toBe(false);
  });

  it("still detects a short history with a refund", () => {
    const series = [...months(7, 10), refund("2026-08-20")];
    expect(hasEnoughHistory(series)).toBe(true);
    expect(detectRecurrence(series, TODAY)).not.toBe(null);
  });

  it("keeps a missed month Overdue with a refund on file", () => {
    const series = [...months(1, 10), refund("2026-10-09")];
    expect(detectRecurrence(series, "2026-11-14")!.isOverdue).toBe(true);
    expect(detectRecurrence(months(1, 10), "2026-11-14")!.isOverdue).toBe(true);
  });

  it("follows the main sign of an income-style series", () => {
    const pay = (date: string): SeriesPoint => ({
      date,
      currency: "USD",
      amount: 2000,
    });
    const verdict = detectRecurrence(
      [
        pay("2026-08-01"),
        pay("2026-09-01"),
        pay("2026-10-01"),
        charge("2026-09-15"),
      ],
      TODAY,
    )!;
    expect(verdict.nextExpected).toBe("2026-11-01");
  });
});
