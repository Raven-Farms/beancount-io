import type { RecurrenceVerdict } from "../screens/merchants-screen/selectors/detect-recurrence";
import { resolveRecurringVerdict } from "../screens/merchants-screen/selectors/resolve-recurring";

const DETECTION: RecurrenceVerdict = {
  cadence: "monthly",
  typicalAmountByCurrency: { USD: -10 },
  isApproximate: false,
  nextExpected: "2024-07-01",
  isOverdue: false,
};

describe("resolveRecurringVerdict", () => {
  it("falls through to detection when no override is set", () => {
    expect(resolveRecurringVerdict(DETECTION, null, true)).toEqual({
      isRecurring: true,
      cadence: "monthly",
      detection: DETECTION,
      source: "detection",
    });
    expect(resolveRecurringVerdict(null, null, true)).toEqual({
      isRecurring: false,
      cadence: null,
      detection: null,
      source: "none",
    });
  });

  it("lets a recurring override beat a null detection (irregular cadence)", () => {
    // Enough dates were analysed and no steady pattern emerged.
    expect(resolveRecurringVerdict(null, "recurring", true)).toEqual({
      isRecurring: true,
      cadence: "irregular",
      detection: null,
      source: "override",
    });
  });

  it("calls a marked payee's cadence unknown when its history is too short", () => {
    // Two identical monthly payments are not irregular (w0/039).
    expect(resolveRecurringVerdict(null, "recurring", false)).toEqual({
      isRecurring: true,
      cadence: "unknown",
      detection: null,
      source: "override",
    });
  });

  it("does not let short history alone make a payee recurring", () => {
    expect(resolveRecurringVerdict(null, null, false).isRecurring).toBe(false);
    expect(
      resolveRecurringVerdict(null, "notRecurring", false).isRecurring,
    ).toBe(false);
  });

  it("lets a recurring override keep the detected cadence when present", () => {
    expect(resolveRecurringVerdict(DETECTION, "recurring", true)).toEqual({
      isRecurring: true,
      cadence: "monthly",
      detection: DETECTION,
      source: "override",
    });
  });

  it("lets a notRecurring override hide a positive detection", () => {
    expect(resolveRecurringVerdict(DETECTION, "notRecurring", true)).toEqual({
      isRecurring: false,
      cadence: null,
      detection: DETECTION,
      source: "override",
    });
  });
});
