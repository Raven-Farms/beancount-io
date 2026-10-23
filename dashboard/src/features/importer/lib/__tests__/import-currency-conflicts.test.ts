import { describe, expect, it } from "vitest";
import { amountCurrencySymbol } from "../../utils/csv-validator";
import { findImportCurrencyConflicts } from "../import-currency-conflicts";

/**
 * Smart Import stripped `€`/`£` to parse the number and then posted every row
 * in the one chosen Currency, so `€-1.25` under USD was prepared as
 * -1.25 USD (w4/m44). The symbol table is the CLI's (w3/421).
 */
const POUND = ["GBP", "GIP", "FKP", "SHP", "EGP"];

describe("amountCurrencySymbol", () => {
  it.each([
    ["€-1.25", "€", ["EUR"]],
    ["-4,50 €", "€", ["EUR"]],
    ["(€1,234.56)", "€", ["EUR"]],
    ["£2.50", "£", POUND],
    ["₩1,000", "₩", ["KRW", "KPW"]],
    ["₹ 99", "₹", ["INR"]],
  ])("reads %s as %s", (cell, symbol, currencies) => {
    expect(amountCurrencySymbol(cell)).toEqual({ symbol, currencies });
  });

  it.each(["-1.25", "$5.00", "¥500", "US$12", "1.000,00"])(
    "names no currency for %s",
    (cell) => {
      // `$` and `¥` are shared by several currencies, so they never refuse.
      expect(amountCurrencySymbol(cell)).toBeNull();
    },
  );
});

describe("findImportCurrencyConflicts", () => {
  const row = (rowIndex: number, amountInput: string, selected = true) => ({
    rowIndex,
    amountInput,
    selected,
  });

  it("groups selected rows whose symbol rules the currency out, by symbol", () => {
    const rows = [row(0, "€-1.25"), row(1, "£2.50"), row(2, "€3"), row(3, "4")];

    expect(findImportCurrencyConflicts(rows, "USD")).toEqual([
      { symbol: "€", currencies: ["EUR"], rows: [1, 3] },
      { symbol: "£", currencies: POUND, rows: [2] },
    ]);
    expect(findImportCurrencyConflicts(rows, "EUR")).toEqual([
      { symbol: "£", currencies: POUND, rows: [2] },
    ]);
    // `£` is also the Egyptian pound, so EGP is not a conflict.
    expect(findImportCurrencyConflicts([row(0, "£2.50")], "EGP")).toEqual([]);
  });

  it("ignores deselected rows", () => {
    expect(
      findImportCurrencyConflicts([row(0, "€-1.25", false)], "USD"),
    ).toEqual([]);
  });
});
