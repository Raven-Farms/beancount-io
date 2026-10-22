import { withMonthToDateStatement } from "../month-to-date-statement";
import { selectRangedAccountTree } from "../select-ranged-account-tree";

// w21/523: October's Expenses bar counted a 400.00 bill pre-entered for the
// 30th, while Home's Spending stopped at today (the 22nd).
const point = (date: string, accounts: Record<string, string>) => ({
  date,
  balance: {},
  accountBalances: Object.fromEntries(
    Object.entries(accounts).map(([account, amount]) => [
      account,
      { USD: amount },
    ]),
  ),
});
const today = "2026-10-22";

const whole = {
  incomeData: [] as ReturnType<typeof point>[],
  expensesData: [
    point("2026-09-30", { "Expenses:QaSpend": "300.00" }),
    point("2026-10-31", { "Expenses:QaSpend": "529.00" }),
  ],
  netProfitData: [point("2026-09-30", {}), point("2026-10-31", {})],
};
const toToday = {
  incomeData: [] as ReturnType<typeof point>[],
  expensesData: [point("2026-10-22", { "Expenses:QaSpend": "129.00" })],
  netProfitData: [point("2026-10-22", {})],
};

describe("withMonthToDateStatement", () => {
  it("reads this month to today and keeps the earlier months", () => {
    const merged = withMonthToDateStatement(whole, toToday, today);
    expect(merged?.expensesData.map((p) => p.date)).toEqual([
      "2026-09-30",
      "2026-10-22",
    ]);
    const tree = selectRangedAccountTree(
      "USD",
      merged?.expensesData ?? [],
      "1M",
      "expenses",
      "2026-10",
    );
    // Home's "This month" for the same rows.
    expect(tree.total).toBe(129);
  });

  it("is the statement as it came until the to-today read lands", () => {
    expect(withMonthToDateStatement(whole, undefined, today)).toBe(whole);
    expect(withMonthToDateStatement(undefined, toToday, today)).toBe(undefined);
  });

  it("drops this month when nothing happened by today", () => {
    const merged = withMonthToDateStatement(
      whole,
      { incomeData: [], expensesData: [], netProfitData: [] },
      today,
    );
    expect(merged?.expensesData.map((p) => p.date)).toEqual(["2026-09-30"]);
  });
});
