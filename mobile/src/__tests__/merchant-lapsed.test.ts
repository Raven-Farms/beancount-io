import {
  detectRecurrence,
  type SeriesPoint,
} from "../screens/merchants-screen/selectors/detect-recurrence";
import { buildMerchantSections } from "../screens/merchants-screen/selectors/merchant-sections";
import { merchantRowText } from "../screens/merchants-screen/merchant-row-text";
import type { MerchantListItem } from "../screens/merchants-screen/selectors/merchant-sections";
import { en } from "../translations/en";

// w21/267: a cancelled subscription stayed red "Overdue" at the top of
// Recurring for up to three years.
const monthly = (dates: string[]): SeriesPoint[] =>
  dates.map((date) => ({ date, currency: "USD", amount: -10 }));

const HULU = monthly([
  "2023-11-08",
  "2023-12-08",
  "2024-01-08",
  "2024-02-08",
  "2024-03-08",
]);
const NETFLIX = monthly([
  "2026-07-15",
  "2026-08-15",
  "2026-09-15",
  "2026-10-15",
]);
const TODAY = "2026-10-21";

describe("a stopped series is lapsed, not overdue", () => {
  it("marks Hulu lapsed with its last payment", () => {
    const hulu = detectRecurrence(HULU, TODAY)!;
    expect(hulu.isLapsed).toBe(true);
    expect(hulu.isOverdue).toBe(false);
    expect(hulu.lastPaid).toBe("2024-03-08");
  });

  it("still reads a real one-cycle miss as Overdue", () => {
    const missed = detectRecurrence(NETFLIX, "2026-11-25")!;
    expect(missed.isOverdue).toBe(true);
    expect(missed.isLapsed).toBe(false);
    // Two periods past the expected date is still a miss, three is a stop.
    const late = detectRecurrence(NETFLIX, "2027-01-10")!;
    expect(late.isOverdue).toBe(true);
    const stopped = detectRecurrence(NETFLIX, "2027-02-20")!;
    expect(stopped.isLapsed).toBe(true);
    expect(stopped.isOverdue).toBe(false);
  });

  it("keeps a series live while the next payment is pre-entered", () => {
    const withScheduled = [...HULU, ...monthly(["2026-12-08"])];
    const verdict = detectRecurrence(withScheduled, TODAY)!;
    expect(verdict.isLapsed).toBe(false);
    expect(verdict.isOverdue).toBe(true);
  });

  it("sorts lapsed below live series and keeps overdue first", () => {
    const merchants = ["Hulu", "Netflix"].map((payee) => ({
      payee,
      transactionCount: 5,
      firstDate: "2023-11-08",
      lastDate: payee === "Hulu" ? "2024-03-08" : "2026-10-15",
    }));
    const detections = new Map([
      ["hulu", detectRecurrence(HULU, TODAY)],
      ["netflix", detectRecurrence(NETFLIX, TODAY)],
    ]);
    const sections = buildMerchantSections(
      merchants,
      detections,
      new Set(["hulu", "netflix"]),
      () => null,
      "",
      "alphabetical",
    );
    expect(sections[0]!.data.map((item) => item.merchant.payee)).toEqual([
      "Netflix",
      "Hulu",
    ]);
  });

  it("reads Last paid, not Overdue, on a lapsed row", () => {
    const t = ((key: string, options?: Record<string, unknown>) =>
      options ? `${key}(${options.date})` : key) as never;
    const item = {
      merchant: { payee: "Hulu", transactionCount: 5, lastDate: "2024-03-08" },
      resolved: {
        isRecurring: true,
        cadence: "monthly",
        detection: detectRecurrence(HULU, TODAY),
      },
      inRecurringSection: true,
    } as unknown as MerchantListItem;
    const text = merchantRowText(item, t, "en", TODAY);
    expect(text.trailingMeta?.startsWith("merchantsLastPaid(")).toBe(true);
    expect(text.trailingOverdue).toBe(false);
    expect(en.merchantsLastPaid).toBe("Last paid {{date}}");
  });
});
