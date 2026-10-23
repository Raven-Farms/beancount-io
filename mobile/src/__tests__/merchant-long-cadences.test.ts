import {
  detectRecurrence,
  type SeriesPoint,
} from "../screens/merchants-screen/selectors/detect-recurrence";
import { cadenceLabelKey } from "../screens/merchants-screen/selectors/merchant-sections";
import { en } from "../translations/en";

// w21/269: bills every two or six months fell between the monthly and
// quarterly bands and were never detected.
const on = (amount: number, dates: string[]): SeriesPoint[] =>
  dates.map((date) => ({ date, currency: "USD", amount }));
const TODAY = "2026-10-21";

describe("every-two-months and every-six-months bills", () => {
  it("detects semi-annual insurance with the right next date", () => {
    const verdict = detectRecurrence(
      on(-612, [
        "2024-04-01",
        "2024-10-01",
        "2025-04-01",
        "2025-10-01",
        "2026-04-01",
        "2026-10-01",
      ]),
      TODAY,
    )!;
    expect(verdict.cadence).toBe("semiannual");
    expect(verdict.nextExpected).toBe("2027-04-01");
    expect(verdict.isOverdue).toBe(false);
  });

  it("detects a bimonthly bill on the 12th", () => {
    const verdict = detectRecurrence(
      on(-84.2, [
        "2025-10-12",
        "2025-12-12",
        "2026-02-12",
        "2026-04-12",
        "2026-06-12",
        "2026-08-12",
        "2026-10-12",
      ]),
      TODAY,
    )!;
    expect(verdict.cadence).toBe("bimonthly");
    expect(verdict.nextExpected).toBe("2026-12-12");
  });

  it("leaves the neighbouring cadences alone", () => {
    const quarterly = detectRecurrence(
      on(-84.2, ["2026-01-12", "2026-04-12", "2026-07-12", "2026-10-12"]),
      TODAY,
    )!;
    expect(quarterly.cadence).toBe("quarterly");
    expect(quarterly.nextExpected).toBe("2027-01-12");
    const monthly = detectRecurrence(
      on(-9, ["2026-08-05", "2026-09-05", "2026-10-05"]),
      TODAY,
    )!;
    expect(monthly.cadence).toBe("monthly");
  });

  it("has a label for each", () => {
    expect(cadenceLabelKey("bimonthly")).toBe("merchantsCadenceBimonthly");
    expect(cadenceLabelKey("semiannual")).toBe("merchantsCadenceSemiannual");
    expect(en.merchantsCadenceBimonthly).toBe("Every 2 months");
    expect(en.merchantsCadenceSemiannual).toBe("Every 6 months");
  });
});
