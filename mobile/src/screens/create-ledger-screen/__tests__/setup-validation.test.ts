import fs from "fs";
import path from "path";
import { isHistoryStart, isSetupCurrency, setupFields } from "../setup-presets";

// w21/107: currency and "Books begin" took any text; a typo dead-ended on
// Review in the server's words, and 2026-04-31 reached the ledger.
describe("Create Ledger's currency and start date", () => {
  it("accepts only currencies the server does", () => {
    expect(isSetupCurrency("USD")).toBe(true);
    expect(isSetupCurrency("eur")).toBe(true);
    expect(isSetupCurrency("US")).toBe(false);
    expect(isSetupCurrency("XYZ")).toBe(false);
  });

  it("accepts only real days, or nothing", () => {
    expect(isHistoryStart("2026-04-01")).toBe(true);
    expect(isHistoryStart("2024-02-29")).toBe(true);
    expect(isHistoryStart("")).toBe(true);
    expect(isHistoryStart("2026-4-1")).toBe(false);
    expect(isHistoryStart("2026-04-31")).toBe(false);
    expect(isHistoryStart("2026-02-30")).toBe(false);
  });

  it("refuses them on the form with localized messages", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "create-ledger-screen.tsx"),
      "utf8",
    );
    expect(source.includes('message: t("createLedgerCurrencyInvalid"),')).toBe(
      true,
    );
    expect(
      source.includes('message: t("createLedgerHistoryStartInvalid"),'),
    ).toBe(true);
    expect(source.includes("{errors.currency?.message ? (")).toBe(true);
    expect(source.includes("{errors.historyStart?.message ? (")).toBe(true);
  });
});

// w21/330: the form's checks trim, but the server's validator does not.
describe("setupFields", () => {
  it('submits " USD" as USD and a padded date as the date', () => {
    expect(
      setupFields({ currency: " usd ", historyStart: " 2026-10-21 " }),
    ).toEqual({ operatingCurrency: "USD", historyStart: "2026-10-21" });
  });

  it("falls back to USD and to today for blanks", () => {
    expect(setupFields({ currency: "   ", historyStart: "  " })).toEqual({
      operatingCurrency: "USD",
      historyStart: undefined,
    });
  });
});

describe("the setup payload", () => {
  it("is built through setupFields", () => {
    const screen = fs
      .readFileSync(
        path.join(__dirname, "..", "create-ledger-screen.tsx"),
        "utf8",
      )
      .replace(/\s+/gu, "");
    expect(screen.includes("...setupFields(values),")).toBe(true);
  });
});
