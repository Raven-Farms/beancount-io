import fs from "fs";
import path from "path";
import { currentIntervalItem, currentPeriodRange } from "../budget-selectors";

const row = (date: string, spent = 0) => ({ date, balance: { USD: spent } });

// w21/364: the month-long window ends on rows for intervals that have not
// begun, and the panel read the last one: a weekly budget showed next week's
// empty row as "$0 spent".
describe("currentIntervalItem", () => {
  // The ledger dates each interval's row at its period's last day (w21/469).
  const weekly = [
    row("2026-10-11"), // Oct 5 – 11
    row("2026-10-18"), // Oct 12 – 18
    row("2026-10-25", 80), // Oct 19 – 25
    row("2026-11-01"), // Oct 26 – Nov 1
  ];

  it("reads the week in progress, not the month's last week", () => {
    expect(currentIntervalItem(weekly, "2026-10-21")?.date).toBe("2026-10-25");
    expect(currentIntervalItem(weekly, "2026-10-21")?.balance.USD).toBe(80);
  });

  it("reads the first day of an interval and the last day of it", () => {
    expect(currentIntervalItem(weekly, "2026-10-19")?.date).toBe("2026-10-25");
    expect(currentIntervalItem(weekly, "2026-10-25")?.date).toBe("2026-10-25");
    expect(currentIntervalItem(weekly, "2026-10-26")?.date).toBe("2026-11-01");
  });

  it("reads the month in progress for a monthly budget (w21/469)", () => {
    // Months are dated at their last day: on 2026-10-21 October's row, 10-31,
    // not September's, 09-30.
    const monthly = [
      row("2026-08-31"),
      row("2026-09-30"),
      row("2026-10-31", 288),
      row("2026-11-30"),
    ];
    expect(currentIntervalItem(monthly, "2026-10-21")?.date).toBe("2026-10-31");
    expect(currentIntervalItem(monthly, "2026-10-21")?.balance.USD).toBe(288);
    expect(currentIntervalItem(monthly, "2026-10-01")?.date).toBe("2026-10-31");
    expect(currentIntervalItem(monthly, "2026-10-31")?.date).toBe("2026-10-31");
    expect(currentIntervalItem(monthly, "2026-11-01")?.date).toBe("2026-11-30");
  });

  it("reads the to-today row when the read ends today", () => {
    // The period-in-progress read is clipped at today, so its row is dated today.
    expect(
      currentIntervalItem([row("2026-10-21", 288)], "2026-10-21")?.balance.USD,
    ).toBe(288);
  });

  it("reads today's row of a daily budget", () => {
    const daily = ["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-31"].map(
      (date) => row(date),
    );
    expect(currentIntervalItem(daily, "2026-10-21")?.date).toBe("2026-10-21");
  });

  it("reads the clipped first week of the year", () => {
    // A weekly period spanning New Year ends on the first Sunday.
    const items = [row("2026-01-04", 5), row("2026-01-11"), row("2026-01-18")];
    expect(currentIntervalItem(items, "2026-01-03")?.date).toBe("2026-01-04");
  });

  it("is null when every row has ended, and for no rows", () => {
    expect(currentIntervalItem([row("2026-10-11")], "2026-10-21")).toBe(null);
    expect(currentIntervalItem([], "2026-10-21")).toBe(null);
  });

  it("agrees with the period the panel prices", () => {
    // The row picked ends at the period's end for a weekly cadence.
    const { end } = currentPeriodRange("week", "2026-10-21");
    expect(currentIntervalItem(weekly, "2026-10-21")?.date).toBe(end);
  });

  it("is what the Home panel reads", () => {
    const hook = fs
      .readFileSync(
        path.join(__dirname, "../../../home-screen/hooks/use-budget-panel.ts"),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(
      hook.includes("constlast=items?currentIntervalItem(items,today):null;"),
    ).toBe(true);
  });
});
