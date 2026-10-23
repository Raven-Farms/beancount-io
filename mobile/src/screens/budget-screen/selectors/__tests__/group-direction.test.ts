import { groupDirection, type BudgetGroup } from "../budget-selectors";
import { selectBudgetCardStats } from "../select-budget-card-stats";
import { selectBudgetPanelRows } from "../../../home-screen/selectors/select-budget-panel";

// w21/394: zeroing an income target stores "0", whose sign says nothing, and the
// card then ran on expense rules: a missed month turned green.
function group(
  account: string,
  history: Array<[string, string]>,
  interval = "monthly",
): BudgetGroup {
  const last = history[history.length - 1][1];
  return {
    account,
    interval,
    currency: "USD",
    amount: last,
    value: Number.parseFloat(last),
    entry_hash: "hash",
    budgetHistory: history.map(([date, amount]) => ({
      date,
      interval,
      amount,
      entry_hash: `${date}-hash`,
    })),
  };
}

const zeroedIncome = group("Income:QaSal", [
  ["2026-01-01", "-3000 USD"],
  ["2026-10-01", "0 USD"],
]);

describe("groupDirection", () => {
  it("reads the newest entry that has a sign, not the amount in effect", () => {
    expect(groupDirection(zeroedIncome)).toBe(-1);
    expect(
      groupDirection(
        group("Expenses:Food", [
          ["2026-01-01", "500 USD"],
          ["2026-10-01", "0 USD"],
        ]),
      ),
    ).toBe(1);
  });

  it("follows the amount in effect when it has a sign, and a lone zero is a cap", () => {
    expect(
      groupDirection(group("Income:Pay", [["2026-01-01", "-100 USD"]])),
    ).toBe(-1);
    expect(
      groupDirection(group("Expenses:Food", [["2026-01-01", "100 USD"]])),
    ).toBe(1);
    expect(
      groupDirection(group("Expenses:Food", [["2026-01-01", "0 USD"]])),
    ).toBe(1);
  });

  it("marks a missed month of a zeroed income target unfavourable on the card", () => {
    // September earned 1,000 against a 3,000 target: it missed.
    const stats = selectBudgetCardStats(
      zeroedIncome,
      [{ date: "2026-09-30", actual: 1000, budget: 3000 }],
      "2026-10-21",
    );
    expect(stats.favorable).toBe(false);
  });

  it("keeps the panel's row an income row", () => {
    const [row] = selectBudgetPanelRows(
      [{ group: zeroedIncome, actual: -1000, periodEnd: "2026-10-31" }],
      3,
      "2026-10-31",
    );
    expect(row.income).toBe(true);
  });
});
