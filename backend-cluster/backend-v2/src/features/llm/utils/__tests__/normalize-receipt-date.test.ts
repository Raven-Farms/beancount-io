import fs from "fs";
import path from "path";
import { normalizeReceiptDate } from "../normalize-receipt-date";

// w21/285: the parse schema's date is an unconstrained string, so a receipt
// date could reach clients in any shape.
describe("normalizeReceiptDate", () => {
  it("keeps a valid ISO date", () => {
    expect(normalizeReceiptDate("2026-10-21")).toBe("2026-10-21");
    expect(normalizeReceiptDate("2024-02-29")).toBe("2024-02-29");
  });

  it("normalises the common year-first forms", () => {
    expect(normalizeReceiptDate("2026/10/21")).toBe("2026-10-21");
    expect(normalizeReceiptDate("2026.10.21")).toBe("2026-10-21");
    expect(normalizeReceiptDate("2026-10-21T14:32:00")).toBe("2026-10-21");
    expect(normalizeReceiptDate("2026-10-21 14:32")).toBe("2026-10-21");
    expect(normalizeReceiptDate("2026-1-5")).toBe("2026-01-05");
  });

  it("drops what it cannot read unambiguously", () => {
    for (const raw of [
      "21/10/2026",
      "10/21/2026",
      "yesterday",
      "2026-13-01",
      "2026-02-30",
      "2025-02-29",
      "2026-10",
      "",
      "   ",
    ]) {
      expect(normalizeReceiptDate(raw)).toBe(null);
    }
    expect(normalizeReceiptDate(null)).toBe(null);
    expect(normalizeReceiptDate(undefined)).toBe(null);
  });
});

describe("parseReceipt", () => {
  it("returns the normalised date, not the model's string", () => {
    const service = fs.readFileSync(
      path.join(__dirname, "..", "..", "service", "llm-service.ts"),
      "utf8",
    );
    expect(service.includes("date: normalizeReceiptDate(txn.date),")).toBe(
      true,
    );
  });
});
