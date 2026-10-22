import fs from "fs";
import path from "path";
import {
  closeDatesOf,
  closedBefore,
} from "../../../../common/account-close-dates";
import {
  budgetForInterval,
  calculateBudgetForInterval,
  prepareBudgetHistory,
  type BudgetHistoryEntry,
} from "../budget-selectors";

// w21/398: a budget on a closed account kept running: a former job's income
// target went red every month after the close and outranked real overspends.
const history: BudgetHistoryEntry[] = [
  {
    date: "2026-01-01",
    interval: "monthly",
    amount: "-3000 USD",
    entry_hash: "h1",
  },
];

describe("a budget on an account that closed", () => {
  it("applies in full until the close, and nothing for later periods", () => {
    const prepared = prepareBudgetHistory(history);
    const at = (end: string, endsOn?: string) =>
      budgetForInterval(
        end,
        "monthly",
        prepared,
        "2026-10-21",
        undefined,
        endsOn,
      );
    expect(at("2026-05-31", "2026-06-30")).toBe(-3000);
    expect(at("2026-06-30", "2026-06-30")).toBe(-3000);
    expect(at("2026-07-31", "2026-06-30")).toBe(0);
    expect(at("2026-10-31", "2026-06-30")).toBe(0);
    // Without a close date it runs on, as before.
    expect(at("2026-07-31")).toBe(-3000);
  });

  it("budgets the period containing the close only up to it", () => {
    const partial = calculateBudgetForInterval(
      "2026-06-30",
      "monthly",
      history,
      "2026-10-21",
      undefined,
      "2026-06-15",
    );
    // 15 of June's 30 days.
    expect(Math.round(partial)).toBe(-1500);
  });

  it("is closed before a day only once that day has passed", () => {
    const closeDates = closeDatesOf([
      { account: "Income:Salary:OldCo", closedAt: "2026-06-30" },
    ]);
    expect(closedBefore("Income:Salary:OldCo", "2026-07-01", closeDates)).toBe(
      true,
    );
    expect(closedBefore("Income:Salary:OldCo", "2026-06-30", closeDates)).toBe(
      false,
    );
    expect(closedBefore("Income:Salary", "2026-10-21", closeDates)).toBe(false);
  });

  it("the card ends its budget at the close and Home leaves the budget out", () => {
    const read = (relative: string) =>
      fs
        .readFileSync(path.join(__dirname, "../../..", relative), "utf8")
        .replace(/\s+/g, "");
    expect(
      read("budget-screen/components/budget-group-card.tsx").includes(
        "endsOn:closeDates.get(group.account),",
      ),
    ).toBe(true);
    const home = read("home-screen/components/budget-card.tsx");
    expect(
      home.includes(
        "groups.filter((g)=>!closedBefore(g.account,today,closeDates))",
      ),
    ).toBe(true);
    expect(home.includes("groups:liveGroups,")).toBe(true);
  });
});

// w21/399: an income target's stored negative text printed unformatted in the
// history rows, the Delete alert and the Update placeholder.
describe("a budget entry's amount in history", () => {
  const { formatBudgetEntryAmount } = require("../budget-selectors");

  it("reads as the magnitude, grouped, with its currency", () => {
    expect(formatBudgetEntryAmount("-4250.50 USD", "USD")).toBe("$4,250.50");
    expect(formatBudgetEntryAmount("4250.50 USD", "USD")).toBe("$4,250.50");
    expect(formatBudgetEntryAmount("-300 USD", "USD")).toBe("$300.00");
  });

  it("keeps a fractional commodity's own precision and a missing currency", () => {
    expect(formatBudgetEntryAmount("-0.003 BTC", "BTC")).toBe("0.003 BTC");
    expect(formatBudgetEntryAmount("-500", "USD")).toBe("$500.00");
    expect(formatBudgetEntryAmount("lots", "USD")).toBe("lots");
  });

  it("is what the row, the alert and the Delete label print", () => {
    const src = fs
      .readFileSync(
        path.join(__dirname, "../../components/budget-history-rows.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(src.split("formatBudgetEntryAmount(").length - 1).toBe(3);
    expect(/\{row\.amount\}|amount:row\.amount/.test(src)).toBe(false);
  });
});
