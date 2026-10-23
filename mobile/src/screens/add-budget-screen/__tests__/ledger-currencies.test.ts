import fs from "fs";
import path from "path";
import {
  budgetCurrencyOptions,
  defaultBudgetCurrency,
} from "../currency-options";

// w21/395: Add Budget offered only operating currencies, with a blind USD
// fallback, so a EUR ledger without `operating_currency` budgeted in USD and read
// $0 spent against its real spending.
describe("Add Budget's currencies", () => {
  it("offers every commodity the ledger knows after the operating ones", () => {
    expect(
      budgetCurrencyOptions(["USD"], "USD", ["USD", "JPY", "EUR", "BTC"]),
    ).toEqual(["USD", "BTC", "EUR", "JPY"]);
  });

  it("offers a EUR ledger without operating_currency its own commodity, not USD", () => {
    expect(budgetCurrencyOptions([], "EUR", ["EUR"])).toEqual(["EUR"]);
    expect(budgetCurrencyOptions([], "EUR", ["EUR", "GBP"])).toEqual([
      "EUR",
      "GBP",
    ]);
  });

  it("includes a typed commodity and the current value, and USD only for a ledger with none", () => {
    expect(budgetCurrencyOptions(["USD"], "USD", [], ["CHF"])).toEqual([
      "USD",
      "CHF",
    ]);
    expect(budgetCurrencyOptions(["USD", "EUR"], "JPY")).toEqual([
      "USD",
      "EUR",
      "JPY",
    ]);
    expect(budgetCurrencyOptions([], "", [])).toEqual(["USD"]);
  });

  it("starts in the first operating currency, else the ledger's first, else USD", () => {
    expect(defaultBudgetCurrency(["GBP", "USD"], ["EUR"])).toBe("GBP");
    expect(defaultBudgetCurrency([], ["EUR", "JPY"])).toBe("EUR");
    expect(defaultBudgetCurrency([], [])).toBe("USD");
  });

  it("the screen builds its options from the ledger and offers Other", () => {
    const src = fs
      .readFileSync(path.join(__dirname, "..", "add-budget-screen.tsx"), "utf8")
      .replace(/\s+/g, "");
    expect(
      src.includes(
        "defaultBudgetCurrency(currencies,ledgerMeta?.currencies??[])",
      ),
    ).toBe(true);
    expect(
      src.includes(
        "budgetCurrencyOptions(currencies,currency,ledgerMeta?.currencies??[],typedCurrencies,)",
      ),
    ).toBe(true);
    expect(
      src.includes(
        '{value:OTHER_CURRENCY,label:t("openAccountOtherCurrency")}',
      ),
    ).toBe(true);
  });
});
