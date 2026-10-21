import { selectRangedAccountTree } from "../select-ranged-account-tree";
import {
  SAVINGS_ID,
  SHORTFALL_ID,
  transformToSankeyData,
} from "../sankey-data";
import { formatSignedMoneyWithCurrency } from "../../../../common/number-utils";

// w21/055: monthly amounts summed as floats left 10.10 + 20.20 - 30.30 at
// -3.55e-15, so a category that nets to zero stayed as "−$0.00 · 0%" and the
// Sankey drew nodes and a Savings flow out of residue.
const labels = {
  otherLabel: "Other",
  cashFlowLabel: "Cash flow",
  savingsLabel: "Savings",
};
const month = (
  date: string,
  accounts: Record<string, Record<string, number>>,
) => ({
  date,
  accountBalances: accounts,
});

describe("amounts that net to zero over the window", () => {
  it("drop the category from the breakdown", () => {
    const { tree, total } = selectRangedAccountTree(
      "USD",
      [
        month("2026-07", {
          "Expenses:Housing:Rent": { USD: 4000 },
          "Expenses:Entertainment:Streaming": { USD: 10.1 },
        }),
        month("2026-08", { "Expenses:Entertainment:Streaming": { USD: 20.2 } }),
        month("2026-09", {
          "Expenses:Entertainment:Streaming": { USD: -30.3 },
        }),
      ],
      "6M",
      "expenses",
    );
    expect(tree.map((node) => node.account)).toEqual(["Expenses:Housing:Rent"]);
    expect(total).toBe(4000);
  });

  it("draw no Sankey node and no Savings or Shortfall for a break-even window", () => {
    // Reports passes the statement's income and expense series separately.
    const income = selectRangedAccountTree(
      "USD",
      [
        month("2026-07", { "Income:Salary": { USD: -0.1 } }),
        month("2026-08", { "Income:Salary": { USD: -0.2 } }),
      ],
      "6M",
      "income",
    );
    const expenses = selectRangedAccountTree(
      "USD",
      [
        month("2026-07", { "Expenses:Shopping": { USD: 0.1 } }),
        month("2026-08", { "Expenses:Shopping": { USD: 0.2 } }),
        month("2026-09", {
          "Expenses:Food": { USD: 0.3 },
          "Expenses:Shopping": { USD: -0.3 },
        }),
      ],
      "6M",
      "expenses",
    );
    expect(expenses.tree.map((node) => node.account)).toEqual([
      "Expenses:Food",
    ]);
    expect(income.total).toBe(0.3);
    expect(expenses.total).toBe(0.3);
    const data = transformToSankeyData({
      income: income.tree,
      expenses: expenses.tree,
      ...labels,
    });
    const ids = data.nodes.map((node) => node.id);
    expect(ids.includes(SAVINGS_ID)).toBe(false);
    expect(ids.includes(SHORTFALL_ID)).toBe(false);
    expect(ids.some((id) => id.includes("Shopping"))).toBe(false);
    expect(data.links.every((link) => link.value >= 0.005)).toBe(true);
  });
});

describe("money formatting of a residue", () => {
  it("never reads as a signed zero", () => {
    expect(formatSignedMoneyWithCurrency(-3.55e-15, "USD")).toBe("$0.00");
    expect(formatSignedMoneyWithCurrency(-0.004, "USD")).toBe("$0.00");
    expect(formatSignedMoneyWithCurrency(-0.005, "USD")).toBe("-$0.01");
    expect(formatSignedMoneyWithCurrency(-12.5, "USD")).toBe("-$12.50");
    expect(formatSignedMoneyWithCurrency(-3.55e-15, "USD", true)).toBe(
      "+$0.00",
    );
  });
});
