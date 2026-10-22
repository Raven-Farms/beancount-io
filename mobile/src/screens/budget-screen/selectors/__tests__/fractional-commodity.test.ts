import {
  budgetScale,
  calculateBudgetForInterval,
  varianceStatus,
  type BudgetGroup,
} from "../budget-selectors";
import { selectBudgetCardStats } from "../select-budget-card-stats";
import { selectBudgetPanelRows } from "../../../home-screen/selectors/select-budget-panel";

// w21/290: a 0.003 BTC budget was rounded to cents and judged with a half-cent
// tolerance, so a 33% overspend read "On target" and the October budget read 0.
const btc = (
  amount = "0.003 BTC",
  interval = "monthly",
  date = "2025-01-01",
) => [{ date, interval, amount, entry_hash: "h" }];

function group(amount = "0.003 BTC"): BudgetGroup {
  return {
    account: "Expenses:Crypto",
    interval: "monthly",
    currency: "BTC",
    amount,
    value: Number.parseFloat(amount),
    entry_hash: "h",
    budgetHistory: btc(amount),
  };
}

describe("a budget in a fractional commodity", () => {
  it("reads its recorded scale, and never less than cents", () => {
    expect(budgetScale(btc("0.003 BTC"))).toBe(3);
    expect(budgetScale(btc("0.00300000 BTC"))).toBe(8);
    expect(budgetScale(btc("300 USD"))).toBe(2);
    expect(budgetScale([])).toBe(2);
    expect(budgetScale(undefined)).toBe(2);
  });

  it("prorates to today without rounding it to nothing", () => {
    const budget = calculateBudgetForInterval(
      "2026-10-31",
      "monthly",
      btc("0.003 BTC", "monthly", "2026-01-01"),
      "2026-10-21",
    );
    expect(Math.abs(budget - (0.003 * 21) / 31) < 1e-6).toBe(true);
    expect(budget > 0).toBe(true);
  });

  it("judges a 33% overspend as above and a half-spent month as below", () => {
    expect(varianceStatus(0.004 - 0.003, 3)).toBe("above");
    expect(varianceStatus(0.0015 - 0.003, 3)).toBe("below");
    expect(varianceStatus(0, 3)).toBe("on");
    // The budget's own float noise is still on target.
    expect(varianceStatus(1e-12, 3)).toBe("on");
  });

  it("reads Above target for the whole September month", () => {
    const stats = selectBudgetCardStats(group(), [
      { date: "2026-09-30", actual: 0.004, budget: 0.003 },
    ]);
    expect(stats.status).toBe("above");
    expect(Math.round(stats.progressPercent ?? 0)).toBe(133);
  });

  it("leaves USD and the cent tolerance as they were", () => {
    expect(varianceStatus(0.004)).toBe("on");
    expect(varianceStatus(0.006)).toBe("above");
    expect(varianceStatus(-0.006)).toBe("below");
    expect(
      calculateBudgetForInterval("2025-01-31", "monthly", btc("5000 USD")),
    ).toBe(5000);
  });

  it("gives Home a budget for the month in progress, not a zero", () => {
    const [row] = selectBudgetPanelRows(
      [{ group: group(), actual: 0.0015, periodEnd: "2026-10-31" }],
      3,
      "2026-10-21",
    );
    expect(row!.noBudget).toBe(false);
    expect(row!.status).toBe("below");
    expect(row!.scale).toBe(3);
  });
});
