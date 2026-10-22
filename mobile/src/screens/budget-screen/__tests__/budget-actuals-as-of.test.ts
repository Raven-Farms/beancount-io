import fs from "fs";
import path from "path";

/**
 * Static guardrail: budget actuals prorate each period's budget no further
 * than today. The hook cannot be rendered by the unit runner; the proration
 * itself is covered in budget-selectors.test.ts.
 */
describe("useBudgetActuals", () => {
  it("passes today as the end of the budgeted span", () => {
    const source = fs
      .readFileSync(
        path.join(__dirname, "..", "hooks", "use-budget-actuals.ts"),
        "utf8",
      )
      .replace(/\s+/gu, "");
    expect(
      source.includes(
        "budgetForInterval(date,group.interval,history,today,windowStart,endsOn,)",
      ),
    ).toBe(true);
  });
});

// w21/455: the current period's own read pending or failed (every offline day
// after the first) put a $0 actual and a green "Below target" on All.
describe("useBudgetActuals before the current period is known", () => {
  const { currentPeriodKnown } = require("../selectors/budget-selectors");
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", ...parts), "utf8")
      .replace(/\s+/gu, "");

  it("knows it for a window, and for all time only once its read has data", () => {
    expect(currentPeriodKnown("2026-01-01 - 2026-10-21", undefined)).toBe(true);
    expect(currentPeriodKnown(undefined, undefined)).toBe(false);
    expect(currentPeriodKnown(undefined, [])).toBe(true);
    expect(currentPeriodKnown(undefined, [{ date: "2026-10-31" }])).toBe(true);
  });

  it("carries no empty periods through today without it", () => {
    expect(
      read("hooks", "use-budget-actuals.ts").includes(
        "if(time===undefined&&last&&currentPeriodKnown(time,currentData)){",
      ),
    ).toBe(true);
  });

  it("judges nothing on the card until it is known", () => {
    expect(
      read("hooks", "use-budget-actuals.ts").includes(
        "constsettled=!error&&currentPeriodKnown(time,currentData);",
      ),
    ).toBe(true);
    expect(
      read("components", "budget-group-card.tsx").includes(
        "selectBudgetCardStats(group,settled?series:[],today)",
      ),
    ).toBe(true);
  });
});
