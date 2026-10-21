import fs from "fs";
import path from "path";
import { intervalAdjectiveKey } from "../budget-labels";
import { en } from "../../../../translations/en";
import { de } from "../../../../translations/de";
import { ru } from "../../../../translations/ru";

// w21/097: the delete alert lowercased the picker's label into the sentence,
// so it read "Das monatlich Budget" and "Удалить ежемесячно бюджет".
describe("the Delete Budget alert's cadence", () => {
  const say = (catalog: Record<string, unknown>, interval: string) =>
    String(catalog.budgetDeleteMessage).replace(
      "{{interval}}",
      String(catalog[intervalAdjectiveKey(interval)]),
    );

  it("agrees with budget in German and Russian", () => {
    expect(say(de, "monthly").startsWith("Das monatliche Budget")).toBe(true);
    expect(say(ru, "MONTHLY").startsWith("Удалить ежемесячный бюджет")).toBe(
      true,
    );
    expect(say(en, "weekly").startsWith("Delete the weekly budget")).toBe(true);
  });

  it("falls back to monthly for an unknown cadence", () => {
    expect(intervalAdjectiveKey("fortnightly")).toBe(
      "budgetIntervalAdjMonthly",
    );
  });

  it("is what the alert interpolates, not the lowercased picker label", () => {
    const rows = fs.readFileSync(
      path.join(__dirname, "..", "..", "components", "budget-history-rows.tsx"),
      "utf8",
    );
    expect(rows.includes("interval: t(intervalAdjectiveKey(interval)),")).toBe(
      true,
    );
    expect(rows.includes(".toLowerCase()")).toBe(false);
  });
});
