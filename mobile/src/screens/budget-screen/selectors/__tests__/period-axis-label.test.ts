import fs from "fs";
import path from "path";
import { periodAxisLabel } from "../budget-labels";

// w21/096: weekly and daily ticks read US month/day ("3/2") in every language,
// which is 3 February in day-first ones.
describe("periodAxisLabel", () => {
  const t = (key: string) => `month:${key}`;

  it("orders a weekly or daily tick as the locale does", () => {
    // A week is labelled by its Sunday, the day the server sends for a
    // finished week.
    expect(periodAxisLabel("2026-03-08", "weekly", t, "en")).toBe("3/8");
    expect(periodAxisLabel("2026-03-08", "weekly", t, "fr")).toBe("08/03");
    expect(periodAxisLabel("2026-03-02", "daily", t, "de")).toBe("2.3.");
    expect(periodAxisLabel("2026-03-08", "weekly", t, "es")).toBe("8/3");
  });

  it("leaves monthly and yearly ticks alone", () => {
    expect(periodAxisLabel("2026-03-31", "monthly", t, "fr")).toBe("month:03");
    expect(periodAxisLabel("2026-12-31", "yearly", t, "fr")).toBe("2026");
  });

  // w21/219: the current quarter read "OCT" on YTD and 1Y but "DEC" on ALL, and
  // this week 10/21 against 10/25, because a windowed span ends today.
  it("labels a period by its own end, however far the window got into it", () => {
    for (const date of ["2026-10-01", "2026-10-21", "2026-12-31"]) {
      expect(periodAxisLabel(date, "quarterly", t, "en")).toBe("month:12");
    }
    for (const date of ["2026-03-31", "2026-01-01"]) {
      expect(periodAxisLabel(date, "quarterly", t, "en")).toBe("month:03");
    }
    // Monday 2026-10-19 to Sunday 2026-10-25.
    for (const date of ["2026-10-19", "2026-10-21", "2026-10-25"]) {
      expect(periodAxisLabel(date, "weekly", t, "en")).toBe("10/25");
    }
  });

  it("is given the app's language by the budget card", () => {
    const card = fs.readFileSync(
      path.join(__dirname, "..", "..", "components", "budget-group-card.tsx"),
      "utf8",
    );
    expect(
      card.includes("periodAxisLabel(point.date, group.interval, t, locale)"),
    ).toBe(true);
  });
});
