import {
  selectBudgetCardStats,
  selectPointFavorability,
} from "../select-budget-card-stats";
import type { BudgetGroup } from "../budget-selectors";

function group(
  amount: string,
  history: Array<[string, string, string]> = [
    ["2025-01-01", "monthly", amount],
  ],
  interval = "monthly",
): BudgetGroup {
  return {
    account: "Expenses:Food",
    interval,
    currency: "USD",
    amount,
    value: Number.parseFloat(amount),
    entry_hash: "hash",
    budgetHistory: history.map(([date, entryInterval, entryAmount]) => ({
      date,
      interval: entryInterval,
      amount: entryAmount,
      entry_hash: `${date}-hash`,
    })),
  };
}

describe("selectBudgetCardStats", () => {
  it("computes variance against the budget in effect for the charted period", () => {
    // The budget was raised to 500 in February; January must still compare
    // against 310, not against today's amount.
    const stats = selectBudgetCardStats(
      group("500 USD", [
        ["2025-01-01", "monthly", "310 USD"],
        ["2025-02-01", "monthly", "500 USD"],
      ]),
      [{ date: "2025-01-31", actual: 400, budget: 310 }],
    );

    expect(stats.budget).toBe(310);
    expect(stats.actual).toBe(400);
    expect(stats.variance).toBe(90);
    expect(stats.status).toBe("above");
    expect(stats.favorable).toBeFalsy();
  });

  it("treats under target as favorable for an expense budget", () => {
    const stats = selectBudgetCardStats(group("500 USD"), [
      { date: "2025-01-31", actual: 420, budget: 500 },
    ]);

    expect(stats.status).toBe("below");
    expect(stats.favorable).toBeTruthy();
    expect(stats.progressPercent).toBeCloseTo(84, 5);
  });

  it("treats above target as favorable for an income budget", () => {
    const stats = selectBudgetCardStats(
      group("-5000 USD", [["2025-01-01", "monthly", "-5000 USD"]]),
      [{ date: "2025-01-31", actual: 5500, budget: 5000 }],
    );

    expect(stats.budget).toBe(5000);
    expect(stats.status).toBe("above");
    expect(stats.favorable).toBeTruthy();
  });

  it("reports on-target as favorable", () => {
    const stats = selectBudgetCardStats(group("500 USD"), [
      { date: "2025-01-31", actual: 500, budget: 500 },
    ]);

    expect(stats.status).toBe("on");
    expect(stats.favorable).toBeTruthy();
    expect(stats.variance).toBe(0);
  });

  it("falls back to the current amount when nothing is charted", () => {
    const stats = selectBudgetCardStats(group("500 USD"), []);

    expect(stats.budget).toBe(500);
    expect(stats.actual).toBe(null);
    expect(stats.variance).toBe(null);
    expect(stats.status).toBe(null);
    expect(stats.progressPercent).toBe(null);
  });

  it("does not compute a progress percentage against a zero budget", () => {
    const stats = selectBudgetCardStats(
      group("0 USD", [["2025-01-01", "monthly", "0 USD"]]),
      [{ date: "2025-01-31", actual: 120, budget: 0 }],
    );

    expect(stats.progressPercent).toBe(null);
  });
});

// Months before the first budget directive have nothing to be over; their zero
// budget made any spending read red (w21/033).
describe("selectPointFavorability before the budget existed", () => {
  const history = [{ date: "2026-08-01" }, { date: "2026-09-01" }];

  it("leaves a pre-budget period unjudged and judges the rest", () => {
    expect(
      selectPointFavorability(
        [
          { date: "2026-07-31", actual: 120.4, budget: 0 },
          { date: "2026-08-31", actual: 180.85, budget: 300 },
          { date: "2026-09-30", actual: 400, budget: 350 },
        ],
        1,
        history,
      ),
    ).toEqual([null, true, false]);
  });

  it("still judges an explicit zero budget", () => {
    expect(
      selectPointFavorability(
        [{ date: "2026-08-31", actual: 5, budget: 0 }],
        1,
        [{ date: "2026-08-01" }],
      ),
    ).toEqual([false]);
  });

  it("judges a period the first directive starts partway through", () => {
    // Dated by its period start, but carrying a prorated budget.
    expect(
      selectPointFavorability(
        [{ date: "2026-08-01", actual: 50, budget: 150 }],
        1,
        [{ date: "2026-08-15" }],
      ),
    ).toEqual([true]);
  });

  it("draws an unjudged bar neutral", () => {
    const fs = require("fs");
    const path = require("path");
    const chart = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "..",
        "..",
        "..",
        "common",
        "d3",
        "budget-bar-chart-d3.tsx",
      ),
      "utf8",
    );
    expect(chart.includes("favorables[i] === null")).toBe(true);
  });
});
