import fs from "fs";
import path from "path";
import { currentIntervalItem, currentPeriodRange } from "../budget-selectors";

const row = (date: string, spent = 0) => ({ date, balance: { USD: spent } });

// w21/364: the month-long window ends on rows for intervals that have not
// begun, and the panel read the last one: a weekly budget showed next week's
// empty row as "$0 spent".
describe("currentIntervalItem", () => {
  const weekly = [
    row("2026-10-05"),
    row("2026-10-12"),
    row("2026-10-19", 80),
    row("2026-10-26"),
  ];

  it("reads the week in progress, not the month's last week", () => {
    expect(currentIntervalItem(weekly, "2026-10-21")?.date).toBe("2026-10-19");
    expect(currentIntervalItem(weekly, "2026-10-21")?.balance.USD).toBe(80);
  });

  it("reads the first day of an interval and the last day before the next", () => {
    expect(currentIntervalItem(weekly, "2026-10-19")?.date).toBe("2026-10-19");
    expect(currentIntervalItem(weekly, "2026-10-25")?.date).toBe("2026-10-19");
    expect(currentIntervalItem(weekly, "2026-10-26")?.date).toBe("2026-10-26");
  });

  it("reads today's row of a daily budget", () => {
    const daily = ["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-31"].map(
      (date) => row(date),
    );
    expect(currentIntervalItem(daily, "2026-10-21")?.date).toBe("2026-10-21");
  });

  it("reads the clipped first week of the year", () => {
    // A weekly period spanning New Year starts at the window's own start.
    const items = [row("2026-01-01", 5), row("2026-01-05"), row("2026-01-12")];
    expect(currentIntervalItem(items, "2026-01-03")?.date).toBe("2026-01-01");
  });

  it("is null when no interval has begun, and for no rows", () => {
    expect(currentIntervalItem([row("2026-11-02")], "2026-10-21")).toBe(null);
    expect(currentIntervalItem([], "2026-10-21")).toBe(null);
  });

  it("agrees with the period the panel prices", () => {
    // The row picked starts at the period's start for a weekly cadence.
    const { start } = currentPeriodRange("week", "2026-10-21");
    expect(currentIntervalItem(weekly, "2026-10-21")?.date).toBe(start);
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
