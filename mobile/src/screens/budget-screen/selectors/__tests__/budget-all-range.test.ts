import fs from "fs";
import path from "path";
import {
  budgetForInterval,
  periodsThrough,
  prepareBudgetHistory,
  throughCurrentPeriod,
  type BudgetGroup,
} from "../budget-selectors";
import { selectBudgetCardStats } from "../select-budget-card-stats";

// ALL used to end at the ledger's last posting: a budget active since then
// lost its unspent months and the card reported August as the current period
// on 2026-10-20 (w21/010). The series now runs through today, as YTD's does.
const TODAY = "2026-10-20";
const groceries: BudgetGroup = {
  account: "Expenses:Food:Groceries",
  interval: "monthly",
  currency: "USD",
  amount: "300 USD",
  value: 300,
  entry_hash: "hash",
  budgetHistory: [
    {
      date: "2026-08-01",
      interval: "monthly",
      amount: "300 USD",
      entry_hash: "h",
    },
  ],
};

describe("periodsThrough", () => {
  it("adds the periods after the last posting through the current one", () => {
    expect(periodsThrough("2026-08-31", "monthly", TODAY)).toEqual([
      "2026-09-30",
      "2026-10-31",
    ]);
    expect(periodsThrough("2026-08-28", "monthly", TODAY)).toEqual([
      "2026-09-30",
      "2026-10-31",
    ]);
  });

  it("adds nothing when the last posting is in the current period", () => {
    expect(periodsThrough("2026-10-05", "monthly", TODAY)).toEqual([]);
  });

  it("steps by the budget's own interval", () => {
    expect(periodsThrough("2026-10-11", "weekly", TODAY)).toEqual([
      "2026-10-18",
      "2026-10-25",
    ]);
    expect(periodsThrough("2026-03-31", "quarterly", TODAY)).toEqual([
      "2026-06-30",
      "2026-09-30",
      "2026-12-31",
    ]);
  });

  it("never loops on a malformed date", () => {
    expect(periodsThrough("not-a-date", "monthly", TODAY)).toEqual([]);
  });
});

describe("Budget card on ALL", () => {
  it("reports the prorated current period, as YTD does", () => {
    const history = prepareBudgetHistory(groceries.budgetHistory);
    const point = (date: string, actual: number) => ({
      date,
      actual,
      budget: budgetForInterval(date, "monthly", history, TODAY),
    });
    const series = [
      point("2026-08-31", 180.85),
      ...periodsThrough("2026-08-31", "monthly", TODAY).map((date) =>
        point(date, 0),
      ),
    ];
    const stats = selectBudgetCardStats(groceries, series);
    // October prorated to the 20th: 300 × 20/31.
    expect(stats.budget).toBe(193.55);
    expect(stats.actual).toBe(0);
  });

  it("pads only the unwindowed range", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "..", "hooks", "use-budget-actuals.ts"),
      "utf8",
    );
    expect(source.includes("if (time === undefined && last)")).toBe(true);
    expect(
      source.includes("periodsThrough(last.date, group.interval, today)"),
    ).toBe(true);
  });
});

// w21/168: a pre-entered November rent cheque made every card on ALL
// describe November at a budget of 0.
describe("ALL with a future-dated entry", () => {
  it("ends at the period containing today", () => {
    const items = [
      { date: "2026-09-30", balance: {} },
      { date: "2026-10-31", balance: {} },
      { date: "2026-11-30", balance: {} },
    ];
    expect(
      throughCurrentPeriod(items, "monthly", "2026-10-21").map((i) => i.date),
    ).toEqual(["2026-09-30", "2026-10-31"]);
    // Nothing after today: unchanged.
    expect(
      throughCurrentPeriod(items.slice(0, 2), "monthly", "2026-10-21"),
    ).toEqual(items.slice(0, 2));
  });

  it("is applied to the unwindowed range only", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "..", "hooks", "use-budget-actuals.ts"),
      "utf8",
    );
    expect(
      source.includes("? throughCurrentPeriod(fetched, group.interval, today)"),
    ).toBe(true);
  });
});
