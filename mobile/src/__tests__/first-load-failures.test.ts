import fs from "fs";
import path from "path";
import { settleBudgetPanel } from "../screens/home-screen/selectors/select-budget-panel";
import type { BudgetGroup } from "../screens/budget-screen/selectors/budget-selectors";

/**
 * w21/080: with the network down and nothing cached, Reports read $0.00 and
 * "no activity", Accounts said "No accounts", and Home's budget panel invited
 * the user to set a budget or showed "$0.00 / $500.00". Each now shows the
 * failure with Retry, as Home's other cards do (w4/067). The screens need
 * native modules the unit runner cannot load, so their branches are checked on
 * the source; the budget panel's rule is checked as behaviour.
 */
const read = (...parts: string[]) =>
  fs.readFileSync(path.join(__dirname, "..", ...parts), "utf8");

const food: BudgetGroup = {
  account: "Expenses:Food",
  interval: "monthly",
  currency: "USD",
  amount: "500 USD",
  value: 500,
  entry_hash: "food",
  budgetHistory: [
    {
      date: "2026-01-01",
      interval: "monthly",
      amount: "500 USD",
      entry_hash: "food",
    },
  ],
};

describe("the Home budget panel", () => {
  const input = { group: food, actual: null, periodEnd: "2026-10-31" };

  it("fails instead of reading a failed actuals read as $0.00 spent", () => {
    expect(
      settleBudgetPanel(
        [
          { input, failed: true },
          { input: { ...input, actual: 120 }, failed: false },
        ],
        3,
        "2026-10-21",
      ),
    ).toEqual({ rows: [], failed: true });
  });

  it("ranks the rows when every read answered", () => {
    const settled = settleBudgetPanel(
      [{ input: { ...input, actual: 120 }, failed: false }],
      3,
      "2026-10-21",
    );
    expect(settled.failed).toBe(false);
    expect(settled.rows.map((row) => row.actual)).toEqual([120]);
  });

  it("shows the failure before the empty invite", () => {
    const card = read(
      "screens",
      "home-screen",
      "components",
      "budget-card.tsx",
    );
    const failure = card.indexOf("if (groupsFailed) {");
    expect(failure > 0).toBe(true);
    expect(card.indexOf("if (rowsFailed) {") > failure).toBe(true);
    expect(card.indexOf("if (rows.length === 0) {") > failure).toBe(true);
    expect(
      read("screens", "home-screen", "hooks", "use-budget-panel.ts").includes(
        ".catch(() => []);",
      ),
    ).toBe(false);
  });
});

describe("Reports and Accounts", () => {
  it("Reports replaces the statement cards with a retry when nothing loaded", () => {
    const source = read("screens", "reports-screen", "reports-screen.tsx");
    expect(source.includes('statementState === "failed" ? (')).toBe(true);
    expect(
      source.includes(
        "<CardLoadFailure onRetry={() => void incomeRefetch()} />",
      ),
    ).toBe(true);
  });

  it("Accounts shows a retry rather than No accounts", () => {
    const source = read("screens", "accounts-screen", "accounts-screen.tsx");
    expect(source.includes(") : accountsFailed ? (")).toBe(true);
    expect(
      source.includes("<CardLoadFailure onRetry={() => void onRefresh()} />"),
    ).toBe(true);
  });
});
