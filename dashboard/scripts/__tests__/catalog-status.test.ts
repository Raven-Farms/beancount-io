import { describe, expect, it } from "vitest";
import { catalogStatus } from "../lib/catalog-status";

// The report judges a catalog by the CI guards' predicates and allowlist, so a
// message pasted whole from English is not "done" (w0/m3).
const english = {
  "receipt.upload": "Upload Receipt",
  "receipt.format": "CSV · PDF",
  "receipt.balance": "Account Balance",
  "receipt.title": "Receipts",
  "userProfile.openLedgerName": "Open Ledger",
};

describe("catalogStatus", () => {
  it("reports a whole English copy and does not count it as completed", () => {
    const status = catalogStatus(
      {
        "receipt.upload": "Upload Receipt",
        "receipt.format": "CSV · PDF",
        "receipt.balance": "Kontostand",
        "receipt.title": "Belege",
        "userProfile.openLedgerName": "Offenes Hauptbuch",
      },
      english,
      "de",
    );
    expect(status.copiedWhole).toEqual(["receipt.upload"]);
    expect(status.completed).toBe(4);
    expect(status.total).toBe(5);
    expect(status.percentage).toBe(80);
  });

  it("does not report a message identical by design or notation alone", () => {
    const status = catalogStatus(
      {
        "receipt.upload": "Beleg hochladen",
        "receipt.format": "CSV · PDF",
        "receipt.balance": "Kontostand",
        "receipt.title": "Belege",
        // Allowlisted in IDENTICAL_BY_DESIGN: a proper name.
        "userProfile.openLedgerName": "Open Ledger",
      },
      english,
      "de",
    );
    expect(status.copiedWhole).toEqual([]);
    expect(status.percentage).toBe(100);
  });

  it("counts [TODO] keys apart and does not also call them copies", () => {
    const status = catalogStatus(
      {
        "receipt.upload": "[TODO] Upload Receipt",
        "receipt.title": "Belege",
      },
      english,
      "de",
    );
    expect(status.todoCount).toBe(1);
    expect(status.copiedWhole).toEqual([]);
    expect(status.completed).toBe(1);
  });

  it("lists a half-translated message but keeps counting it as completed", () => {
    const status = catalogStatus(
      { "receipt.balance": "Cuenta Balance", "receipt.title": "Recibos" },
      english,
      "es",
    );
    expect(status.halfTranslated).toEqual(["receipt.balance"]);
    expect(status.copiedWhole).toEqual([]);
    expect(status.completed).toBe(2);
  });
});
