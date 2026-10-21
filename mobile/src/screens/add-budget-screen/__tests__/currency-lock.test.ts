import fs from "fs";
import path from "path";
import { budgetCurrencyOptions } from "../currency-options";

// w21/121: Update Budget left Currency editable, so a change started a second
// budget, and a non-operating currency fell back to the picker's first option.
describe("Update Budget's currency", () => {
  it("keeps a non-operating current value among the options", () => {
    expect(budgetCurrencyOptions(["USD", "EUR"], "JPY")).toEqual([
      "USD",
      "EUR",
      "JPY",
    ]);
    expect(budgetCurrencyOptions(["USD", "EUR"], "EUR")).toEqual([
      "USD",
      "EUR",
    ]);
    expect(budgetCurrencyOptions([], "")).toEqual(["USD"]);
  });

  it("is locked with the account when updating", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "add-budget-screen.tsx"),
      "utf8",
    );
    expect(
      source.includes(
        'onPress={isUpdate ? undefined : () => setPicker("currency")}',
      ),
    ).toBe(true);
    expect(source.includes("budgetCurrencyOptions(currencies, currency)")).toBe(
      true,
    );
  });
});
