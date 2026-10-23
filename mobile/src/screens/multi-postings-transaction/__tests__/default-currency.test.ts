import fs from "fs";
import path from "path";
import { ledgerPrimaryCurrency } from "../../../common/currency-util";

// w21/520: New Transaction wrote USD into a ledger without an operating
// currency, where Home, Accounts and Reports already read its own commodity.
describe("New Transaction's default currency", () => {
  it("is the ledger's own currency when no operating currency is set", () => {
    expect(ledgerPrimaryCurrency([], ["EUR"])).toBe("EUR");
    expect(ledgerPrimaryCurrency(["GBP"], ["EUR"])).toBe("GBP");
    expect(ledgerPrimaryCurrency([], [])).toBe("USD");
  });

  it("is what the form uses, from the ledger's commodities", () => {
    const source = fs
      .readFileSync(
        path.join(__dirname, "..", "multi-postings-transaction-screen.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(
      source.includes(
        "constcurrency=ledgerPrimaryCurrency(currencies,ledgerMeta?.currencies??[],);",
      ),
    ).toBe(true);
    expect(source.includes('currencies[0]:"USD"')).toBe(false);
  });
});
