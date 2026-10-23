import fs from "fs";
import path from "path";
import { formatEntryBalances } from "../format-entry-balances";

// w21/092: balances arrive as one string per currency or lot. `[]` rendered
// blank and two currencies ran together as "100.00 USD,50.00 EUR".
describe("formatEntryBalances", () => {
  it("shows an account with no balance yet as zero", () => {
    expect(formatEntryBalances({ "Expenses:Fresh": [] })).toEqual([
      { account: "Expenses:Fresh", amounts: ["0"] },
    ]);
  });

  it("gives each currency its own line", () => {
    expect(
      formatEntryBalances({
        "Assets:Wallet": ["100.00 USD", "50.00 EUR"],
        "Assets:Cash": ["60.00 USD"],
      }),
    ).toEqual([
      { account: "Assets:Wallet", amounts: ["100.00 USD", "50.00 EUR"] },
      { account: "Assets:Cash", amounts: ["60.00 USD"] },
    ]);
  });

  it("keeps a lot string whole", () => {
    expect(
      formatEntryBalances({
        "Assets:Broker": ["10 HOOL {100.00 USD, 2026-01-01}"],
      })[0].amounts,
    ).toEqual(["10 HOOL {100.00 USD, 2026-01-01}"]);
  });

  it("still reads the {number, currency} form", () => {
    expect(
      formatEntryBalances({
        "Assets:Cash": { number: "60.00", currency: "USD" },
      }),
    ).toEqual([{ account: "Assets:Cash", amounts: ["60.00 USD"] }]);
    expect(formatEntryBalances(null)).toEqual([]);
  });

  it("renders the amounts one per line", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "balance-section.tsx"),
      "utf8",
    );
    expect(source.includes("{balance.amounts.map((amount, line) => (")).toBe(
      true,
    );
  });
});
