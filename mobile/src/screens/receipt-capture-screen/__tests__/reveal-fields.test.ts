import { receiptRevealFields } from "../receipt-utils";

// w21/538: the "Receipt read" reveal showed "2026-03-01" and "1234.50".
describe("receiptRevealFields", () => {
  const receipt = { payee: "Edeka", amount: -1234.5, date: "2026-03-01" };

  it("writes the date in the reader's language", () => {
    expect(receiptRevealFields(receipt, "USD", "de").date).toBe("1. März 2026");
    expect(receiptRevealFields(receipt, "USD", "en").date).not.toBe(
      "2026-03-01",
    );
  });

  it("writes the total as positive money in the ledger's currency", () => {
    expect(receiptRevealFields(receipt, "USD", "en").amount).toBe("$1,234.50");
    expect(receiptRevealFields(receipt, "EUR", "en").amount).toBe("€1,234.50");
    expect(
      receiptRevealFields({ ...receipt, amount: 1500 }, "JPY", "en").amount,
    ).toBe("¥1,500");
  });

  it("keeps the payee as read", () => {
    expect(receiptRevealFields(receipt, "USD", "en").payee).toBe("Edeka");
  });
});
