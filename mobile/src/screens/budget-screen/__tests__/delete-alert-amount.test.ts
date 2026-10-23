import fs from "fs";
import path from "path";

// w21/536: the budget Delete alert put the currency of "300.00 USD" on the wrong
// side in Persian; every other amount in a sentence is isolated (w21/095).
describe("the budget Delete alert's amount", () => {
  it("is isolated, so a right-to-left sentence keeps its order", () => {
    const source = fs
      .readFileSync(
        path.join(__dirname, "..", "components", "budget-history-rows.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(
      source.includes(
        "amount:isolateLtr(formatBudgetEntryAmount(amount,group.currency)),",
      ),
    ).toBe(true);
  });
});
