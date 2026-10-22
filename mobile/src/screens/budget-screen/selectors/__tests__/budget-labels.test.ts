import {
  budgetChartSummary,
  intervalLabelKey,
  timeSpanToFilter,
  budgetPanelWindow,
} from "../budget-labels";
import { en } from "../../../../translations/en";

describe("intervalLabelKey", () => {
  it("maps each cadence to its label key, case-insensitively", () => {
    expect(intervalLabelKey("daily")).toBe("budgetIntervalDaily");
    expect(intervalLabelKey("WEEKLY")).toBe("budgetIntervalWeekly");
    expect(intervalLabelKey("monthly")).toBe("budgetIntervalMonthly");
    expect(intervalLabelKey("Quarterly")).toBe("budgetIntervalQuarterly");
    expect(intervalLabelKey("yearly")).toBe("budgetIntervalYearly");
  });

  it("labels an unknown cadence as monthly, matching the proration fallback", () => {
    expect(intervalLabelKey("fortnightly")).toBe("budgetIntervalMonthly");
  });
});

describe("timeSpanToFilter", () => {
  it("sends no filter for all time", () => {
    expect(timeSpanToFilter("all", "2026-08-09")).toBe(undefined);
  });

  it("ends year to date today, so no unstarted period is charted", () => {
    expect(timeSpanToFilter("this-year", "2026-09-13")).toBe(
      "2026-01-01 - 2026-09-13",
    );
  });

  // w21/148: fava's `year-1` resolved on the server's calendar, so on New
  // Year's Day in Tokyo "Last year" charted the year before last.
  it("builds last year from the device's date, whatever the server's zone", () => {
    expect(timeSpanToFilter("last-year", "2027-01-01")).toBe(
      "2026-01-01 - 2026-12-31",
    );
    expect(timeSpanToFilter("last-year", "2026-12-31")).toBe(
      "2025-01-01 - 2025-12-31",
    );
  });

  it("expresses the rolling window as an explicit range", () => {
    expect(timeSpanToFilter("last-12m", "2026-08-09")).toBe(
      "2025-08-09 - 2026-08-09",
    );
  });
});

// Interpolates the real English copy, so a renamed key or a dropped token fails
// here rather than shipping "undefined" into the chart's only spoken text.
// English plural objects pick `one` or `other` by count (w21/098).
const t = (key: string, params?: Record<string, unknown>) => {
  const value = (en as unknown as Record<string, unknown>)[key];
  const text =
    typeof value === "object" && value !== null
      ? (value as Record<string, string>)[params?.count === 1 ? "one" : "other"]
      : String(value);
  return text.replace(/{{(\w+)}}/g, (_match, name: string) =>
    String(params?.[name]),
  );
};

describe("budgetChartSummary", () => {
  it("summarizes the span, the totals, and how many periods missed target", () => {
    expect(
      budgetChartSummary(
        {
          labels: ["JAN", "FEB", "MAR"],
          actuals: [400, 600, 1200],
          budgets: [500, 500, 500],
          favorables: [true, false, false],
          currency: "USD",
        },
        t,
      ),
    ).toBe(
      "Budget versus actual for JAN–MAR. Actual $2.2K of $1.5K budgeted across 3 periods, 2 over target.",
    );
  });

  it("names a single period without a range dash", () => {
    expect(
      budgetChartSummary(
        {
          labels: ["JAN"],
          actuals: [400],
          budgets: [500],
          favorables: [true],
          currency: "USD",
        },
        t,
      ),
    ).toBe(
      "Budget versus actual for JAN. Actual $400 of $500 budgeted across 1 period, 0 over target.",
    );
  });

  it("labels a currency without a symbol by its code", () => {
    expect(
      budgetChartSummary(
        {
          labels: ["JAN"],
          actuals: [400],
          budgets: [500],
          favorables: [true],
          currency: "MUSD",
        },
        t,
      ),
    ).toBe(
      "Budget versus actual for JAN. Actual 400 MUSD of 500 MUSD budgeted across 1 period, 0 over target.",
    );
  });

  it("counts only an explicit false against target, not an unjudged period", () => {
    const summary = budgetChartSummary(
      {
        labels: ["JAN", "FEB"],
        actuals: [100, 100],
        budgets: [100, 100],
        // `undefined` is "no budget to judge against", not "over target".
        favorables: [undefined as unknown as boolean, false],
        currency: "EUR",
      },
      t,
    );
    expect(summary?.endsWith("1 over target.")).toBe(true);
  });

  it("summarizes nothing for an empty series — the placeholder speaks instead", () => {
    expect(
      budgetChartSummary(
        {
          labels: [],
          actuals: [],
          budgets: [],
          favorables: [],
          currency: "USD",
        },
        t,
      ),
    ).toBe(undefined);
  });
});

// w21/063: on 29 February the 1Y start was "2023-02-29", which the server
// refuses, so the view failed all day.
describe("timeSpanToFilter: leap day", () => {
  it("clamps a leap day's start to 28 February", () => {
    expect(timeSpanToFilter("last-12m", "2024-02-29")).toBe(
      "2023-02-28 - 2024-02-29",
    );
  });

  it("keeps every other date as it is", () => {
    expect(timeSpanToFilter("last-12m", "2026-10-21")).toBe(
      "2025-10-21 - 2026-10-21",
    );
    expect(timeSpanToFilter("last-12m", "2025-02-28")).toBe(
      "2024-02-28 - 2025-02-28",
    );
    expect(timeSpanToFilter("last-12m", "2027-03-01")).toBe(
      "2026-03-01 - 2027-03-01",
    );
  });
});

// w21/184: year to date ended on today, a new cache key every day.
describe("budgetPanelWindow", () => {
  it("runs from January to the end of the month, the same all month", () => {
    expect(budgetPanelWindow("2026-10-21")).toBe("2026-01-01 - 2026-10-31");
    expect(budgetPanelWindow("2026-10-01")).toBe(
      budgetPanelWindow("2026-10-31"),
    );
    expect(budgetPanelWindow("2028-02-10")).toBe("2028-01-01 - 2028-02-29");
  });

  it("is what Home's budget panel prices over", () => {
    const hook = require("fs").readFileSync(
      require("path").join(
        __dirname,
        "..",
        "..",
        "..",
        "home-screen",
        "hooks",
        "use-budget-panel.ts",
      ),
      "utf8",
    );
    // The watched day, so the window follows midnight (w21/233).
    expect(hook.includes("budgetPanelWindow(today)")).toBe(true);
  });
});
