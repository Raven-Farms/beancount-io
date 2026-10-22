import { detectRecurrence } from "../../screens/merchants-screen/selectors/detect-recurrence";
import { merchantKey, seriesByMerchant } from "../merchant-key";

/**
 * w21/169: a merchant spelled two ways got recurrence from one spelling's
 * series only — a false Overdue, or no detection at all.
 */
const streaming = (date: string) => ({ date, currency: "USD", amount: 15.49 });

describe("merchantKey with curly quotes", () => {
  it("reads Smart Punctuation's ’ as the apostrophe typed (w21/519)", () => {
    expect(merchantKey("Trader Joe\u2019s")).toBe(merchantKey("Trader Joe's"));
    expect(merchantKey("The \u201cBig\u201d Cafe")).toBe(
      merchantKey('The "Big" Cafe'),
    );
  });
});

describe("seriesByMerchant", () => {
  it("reads drifted spellings as one merchant's history", () => {
    const merged = seriesByMerchant(
      new Map([
        [
          "QaFlix",
          ["01", "02", "03", "04", "05", "06"].map((m) =>
            streaming(`2026-${m}-15`),
          ),
        ],
        [
          "QAFLIX",
          ["07", "08", "09", "10"].map((m) => streaming(`2026-${m}-15`)),
        ],
      ]),
    );
    expect([...merged.keys()]).toEqual(["qaflix"]);
    const verdict = detectRecurrence(merged.get("qaflix")!, "2026-10-21");
    expect(verdict?.cadence).toBe("monthly");
    expect(verdict?.isOverdue).toBe(false);
    expect(verdict?.nextExpected).toBe("2026-11-15");
  });

  it("detects alternating spellings", () => {
    const months = ["03", "04", "05", "06", "07", "08"];
    const merged = seriesByMerchant(
      new Map([
        [
          "QaFlix",
          months
            .filter((_, i) => i % 2 === 0)
            .map((m) => streaming(`2026-${m}-15`)),
        ],
        [
          "QAFLIX",
          months
            .filter((_, i) => i % 2 === 1)
            .map((m) => streaming(`2026-${m}-15`)),
        ],
      ]),
    );
    expect(detectRecurrence(merged.get("qaflix")!, "2026-08-20")?.cadence).toBe(
      "monthly",
    );
  });

  it("keys by the trimmed, case-folded payee", () => {
    expect(merchantKey(" QaFlix ")).toBe("qaflix");
  });
});
