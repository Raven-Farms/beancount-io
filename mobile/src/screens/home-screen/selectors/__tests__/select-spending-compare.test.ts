import fs from "fs";
import path from "path";
import {
  selectSpendingCompare,
  spendingChartSummary,
  spendingWindow,
} from "../select-spending-compare";
import { en } from "../../../../translations/en";

// The card used to sum the newest 200 journal rows, so a month with more
// transactions than that hid last month's spending and capped this month's
// (w21/011). It now reads the Expenses root's monthly totals for the two
// months, which the server sums whole.
const REF = new Date(2026, 9, 20); // 2026-10-20, local time

describe("spendingWindow", () => {
  // w21/184: ending on today made a new cache key every day, so the next day
  // offline found no cached result.
  it("asks for the first of last month through the end of this one", () => {
    expect(spendingWindow(REF)).toBe("2026-09-01 - 2026-10-31");
  });

  it("is the same all month", () => {
    expect(spendingWindow(new Date(2026, 9, 1))).toBe(spendingWindow(REF));
    expect(spendingWindow(new Date(2026, 9, 31))).toBe(spendingWindow(REF));
  });

  it("reaches back across a year boundary in January", () => {
    expect(spendingWindow(new Date(2027, 0, 5))).toBe(
      "2026-12-01 - 2027-01-31",
    );
  });
});

describe("selectSpendingCompare", () => {
  it("returns zeros for no months", () => {
    expect(selectSpendingCompare([], "USD", REF)).toEqual({
      thisMonth: 0,
      lastMonth: 0,
      notInTotal: [],
      thisMonthKey: "2026-10",
      lastMonthKey: "2026-09",
    });
  });

  it("reads last month and this month from their totals, however busy", () => {
    // The repro: one $100 September expense, 205 October expenses of $1.
    const result = selectSpendingCompare(
      [
        { date: "2026-09-30", balance: { USD: 100 } },
        { date: "2026-10-31", balance: { USD: "205.00" } },
      ],
      "USD",
      REF,
    );
    expect(result.lastMonth).toBe(100);
    expect(result.thisMonth).toBe(205);
  });

  it("reads the active currency only", () => {
    const result = selectSpendingCompare(
      [{ date: "2026-10-31", balance: { EUR: 40, USD: 12 } }],
      "EUR",
      REF,
    );
    expect(result.thisMonth).toBe(40);
  });

  it("ignores months outside the two compared", () => {
    const result = selectSpendingCompare(
      [
        { date: "2026-08-31", balance: { USD: 999 } },
        { date: "2026-10-31", balance: { USD: 5 } },
      ],
      "USD",
      REF,
    );
    expect(result.lastMonth).toBe(0);
    expect(result.thisMonth).toBe(5);
  });

  it("treats a month with no balance as no spending", () => {
    const result = selectSpendingCompare(
      [{ date: "2026-09-30", balance: null }],
      "USD",
      REF,
    );
    expect(result.lastMonth).toBe(0);
  });
});

describe("Spending card", () => {
  it("queries the ledger's Expenses root by month over the window", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "..", "components", "spending-card.tsx"),
      "utf8",
    );
    expect(source.includes("useGetLedgerIntervalTotalsQuery")).toBe(true);
    expect(source.includes("accountName: expensesRoot,")).toBe(true);
    expect(source.includes('interval: "month",')).toBe(true);
    expect(source.includes("time: spendingWindow(),")).toBe(true);
    expect(source.includes("useGetLedgerJournalQuery")).toBe(false);
  });
});

// The chart's bars and ticks are not readable on their own; VoiceOver hears
// one summary naming both months and amounts (w21/018).
describe("spendingChartSummary", () => {
  const t = (key: "spendingChartSummary", params: Record<string, string>) =>
    en[key].replace(/\{\{(\w+)\}\}/g, (_, name: string) => params[name]);

  it("names both months and their amounts", () => {
    expect(
      spendingChartSummary({ lastMonth: 100, thisMonth: 205 }, "USD", t),
    ).toBe("Spending: last month $100.00, this month $205.00.");
  });

  it("is the label of the one accessible chart element", () => {
    const read = (...parts: string[]) =>
      fs.readFileSync(path.join(__dirname, ...parts), "utf8");
    expect(
      read("..", "..", "..", "..", "common", "d3", "bar-chart-d3.tsx").includes(
        "<View accessible accessibilityLabel={accessibilityLabel}>",
      ),
    ).toBe(true);
    expect(
      read("..", "..", "components", "spending-card.tsx").includes(
        "accessibilityLabel={spendingChartSummary(",
      ),
    ).toBe(true);
  });
});

// w21/038: a 50 EUR expense in a USD ledger read "This month $0" with no hint.
describe("selectSpendingCompare: other currencies", () => {
  it("names the spending the bars cannot include", () => {
    const result = selectSpendingCompare(
      [
        { date: "2026-10-05", balance: { USD: "12.00", EUR: "50.00" } },
        { date: "2026-09-12", balance: { EUR: "20.10" } },
        // Outside the two months: not counted, not disclosed.
        { date: "2026-08-01", balance: { EUR: "999.00" } },
      ],
      "USD",
      REF,
    );
    expect(result.thisMonth).toBe(12);
    expect(result.lastMonth).toBe(0);
    expect(result.notInTotal).toEqual([
      { currency: "EUR", number: 70.1, scale: 2 },
    ]);
  });

  it("discloses nothing for a single-currency ledger", () => {
    expect(
      selectSpendingCompare(
        [{ date: "2026-10-05", balance: { USD: "12.00" } }],
        "USD",
        REF,
      ).notInTotal,
    ).toEqual([]);
  });
});

describe("spendingChartSummary: other currencies", () => {
  it("speaks the not-in-total line after the amounts", () => {
    const t = (_key: string, params: Record<string, string>) =>
      `${params.lastMonth} then ${params.thisMonth}`;
    expect(
      spendingChartSummary(
        { lastMonth: 0, thisMonth: 12 },
        "USD",
        t,
        "Not in total: 50.00 EUR",
      ),
    ).toBe("$0.00 then $12.00. Not in total: 50.00 EUR");
  });
});
