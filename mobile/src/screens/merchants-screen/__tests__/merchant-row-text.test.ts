import fs from "fs";
import path from "path";
import { merchantRowText } from "../merchant-row-text";
import type { MerchantListItem } from "../selectors/merchant-sections";

/**
 * w21/139: VoiceOver read a Merchants row as the payee alone, dropping its
 * count, Recurring, cadence, typical amount and "Overdue".
 */
const t = ((key: string, options?: Record<string, unknown>) =>
  options ? `${key}(${JSON.stringify(options)})` : key) as never;

const netflix = (inRecurringSection: boolean, isOverdue: boolean) =>
  ({
    merchant: {
      payee: "Netflix",
      transactionCount: 12,
      lastDate: "2026-08-01",
    },
    resolved: {
      isRecurring: true,
      cadence: "monthly",
      detection: {
        cadence: "monthly",
        typicalAmountByCurrency: { USD: 15.99 },
        isApproximate: true,
        nextExpected: "2026-09-01",
        isOverdue,
      },
    },
    inRecurringSection,
  }) as unknown as MerchantListItem;

describe("merchantRowText", () => {
  it("reads a recurring overdue row in full", () => {
    const text = merchantRowText(netflix(true, true), t, "en", "2026-10-21");
    expect(text.accessibilityLabel).toBe(
      [
        "Netflix",
        'merchantsTransactionCount({"count":12})',
        "merchantsRecurringBadge",
        "merchantsCadenceMonthly",
        text.trailingAmount,
        "merchantsOverdue",
      ].join(", "),
    );
    expect(text.trailingAmount?.startsWith("~")).toBe(true);
    expect(text.trailingOverdue).toBe(true);
  });

  it("reads a general-list row as its count, badge and last date", () => {
    const text = merchantRowText(netflix(false, false), t, "en", "2026-10-21");
    expect(text.showBadge).toBe(true);
    expect(text.accessibilityLabel).toBe(
      [
        "Netflix",
        'merchantsTransactionCount({"count":12})',
        "merchantsRecurringBadge",
        text.lastDate,
      ].join(", "),
    );
  });
});

// w21/167: a pre-entered payment read as paid.
describe("a pre-entered payment on the Merchants row", () => {
  it("keeps Overdue and names the scheduled one", () => {
    const item = netflix(true, true);
    (item.resolved.detection as { scheduled?: string }).scheduled =
      "2026-11-01";
    expect(
      merchantRowText(item, t, "en", "2026-10-21").trailingMeta?.startsWith(
        "merchantsOverdue · merchantsScheduled(",
      ),
    ).toBe(true);
  });

  it("labels a last date after today as scheduled", () => {
    const item = netflix(false, false);
    item.merchant.lastDate = "2026-11-01";
    expect(
      merchantRowText(item, t, "en", "2026-10-21").lastDate.startsWith(
        "merchantsScheduled(",
      ),
    ).toBe(true);
  });
});

describe("the Merchants row", () => {
  it("is labelled by merchantRowText, with a testID per payee", () => {
    const row = fs.readFileSync(
      path.join(__dirname, "..", "merchant-row.tsx"),
      "utf8",
    );
    expect(row.includes("merchantRowText(item, t, locale, today)")).toBe(true);
    expect(row.includes("accessibilityLabel={accessibilityLabel}")).toBe(true);
    expect(row.includes("accessibilityLabel={merchant.payee}")).toBe(false);
    expect(row.includes("testID={`merchant-row-${merchant.payee}`}")).toBe(
      true,
    );
  });
});
