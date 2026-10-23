import fs from "fs";
import path from "path";
import { buildBudgetEntry } from "../../budget-screen/build-budget-entry";

// w21/303: an update from a card took its currency from the route, so Done did
// not wait for the ledger's options, and an income target saved before they
// landed went out positive (a spending cap). The screen uses hooks this runner
// cannot execute, so the wiring is checked on its source.
describe("Add Budget waits for the ledger's options before saving", () => {
  const source = fs
    .readFileSync(path.join(__dirname, "..", "add-budget-screen.tsx"), "utf8")
    .replace(/\s+/g, "");

  it("reads the metadata error and requires it to be settled", () => {
    expect(source.includes("error:metaError,}=useLedgerMeta(")).toBe(true);
    expect(
      source.includes(
        "constmetaSettled=ledgerMeta!==undefined||Boolean(metaError);",
      ),
    ).toBe(true);
    const submit = source.slice(source.indexOf("constcanSubmit="));
    expect(
      submit.slice(0, submit.indexOf(";")).includes("&&metaSettled&&"),
    ).toBe(true);
  });

  it("saves the income sign once the root is known, and as typed when it is not", () => {
    const income = {
      account: "Income:Salary",
      interval: "MONTHLY",
      currency: "USD",
      date: new Date(2026, 9, 21),
      number: "5000",
    };
    expect(
      buildBudgetEntry({ ...income, incomeRoot: "Income" }).budget?.amount
        .number,
    ).toBe("-5000");
    expect(buildBudgetEntry(income).budget?.amount.number).toBe("5000");
  });
});
