type GetCurrencySymbol = typeof import("../currency-util").getCurrencySymbol;

describe("getCurrencySymbol", () => {
  let getCurrencySymbol: GetCurrencySymbol;

  beforeAll(() => {
    const currencyIconsPath = require.resolve("currency-icons");
    require.cache[currencyIconsPath] = {
      exports: {
        USD: { symbol: "$" },
        EUR: {},
      },
    } as NodeModule;

    const modulePath = require.resolve("../currency-util");
    delete require.cache[modulePath];
    ({ getCurrencySymbol } = require("../currency-util"));
  });

  afterAll(() => {
    const currencyIconsPath = require.resolve("currency-icons");
    delete require.cache[currencyIconsPath];

    const modulePath = require.resolve("../currency-util");
    delete require.cache[modulePath];
  });

  it("returns the Yuan symbol for CNY regardless of configured icons", () => {
    expect(getCurrencySymbol("CNY")).toBe("¥");
  });

  it("returns the symbol provided by currency-icons when available", () => {
    expect(getCurrencySymbol("USD")).toBe("$");
  });

  it("falls back to an empty string when a symbol is unavailable", () => {
    expect(getCurrencySymbol("EUR")).toBe("");
    expect(getCurrencySymbol("ABC")).toBe("");
  });
});

// w21/415: a ledger without `option "operating_currency"` showed Home as $0.00
// USD with every amount under "Not in total".
describe("ledgerPrimaryCurrency", () => {
  const { ledgerPrimaryCurrency } = require("../currency-util");

  it("is the first operating currency when the ledger declares one", () => {
    expect(ledgerPrimaryCurrency(["GBP", "USD"], ["EUR", "USD"])).toBe("GBP");
  });

  it("is the ledger's own currency when it declares none", () => {
    expect(ledgerPrimaryCurrency([], ["EUR"])).toBe("EUR");
  });

  it("prefers a known currency to a ticker, and falls back to the first commodity", () => {
    expect(ledgerPrimaryCurrency([], ["VTI", "EUR", "JPY"])).toBe("EUR");
    expect(ledgerPrimaryCurrency([], ["VTI", "QZX"])).toBe("VTI");
  });

  it("is USD only for a ledger with no commodity yet", () => {
    expect(ledgerPrimaryCurrency([], [])).toBe("USD");
  });

  it("is what Home, Accounts, Reports and account detail read in", () => {
    const fs = require("fs");
    const path = require("path");
    const read = (relative: string) =>
      fs
        .readFileSync(path.join(__dirname, "../..", relative), "utf8")
        .replace(/\s+/g, "");
    for (const file of [
      "screens/home-screen/home-screen.tsx",
      "screens/accounts-screen/accounts-screen.tsx",
      "screens/reports-screen/reports-screen.tsx",
      "screens/account-detail-screen/account-detail-screen.tsx",
    ]) {
      const src = read(file);
      expect(src.includes("primaryCurrency:currency,")).toBe(true);
      expect(src.includes("getPrimaryCurrency(")).toBe(false);
    }
    expect(
      read("common/hooks/use-ledger-read-context.ts").includes(
        "primaryCurrency:ledgerPrimaryCurrency(ordered.currencies,ledger?.attributes.currencies??[],)",
      ),
    ).toBe(true);
  });
});
