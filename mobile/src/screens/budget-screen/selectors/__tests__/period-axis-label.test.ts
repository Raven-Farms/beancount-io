import fs from "fs";
import path from "path";
import { periodAxisLabel } from "../budget-labels";

// w21/096: weekly and daily ticks read US month/day ("3/2") in every language,
// which is 3 February in day-first ones.
describe("periodAxisLabel", () => {
  const t = (key: string) => `month:${key}`;

  it("orders a weekly or daily tick as the locale does", () => {
    expect(periodAxisLabel("2026-03-02", "weekly", t, "en")).toBe("3/2");
    expect(periodAxisLabel("2026-03-02", "weekly", t, "fr")).toBe("02/03");
    expect(periodAxisLabel("2026-03-02", "daily", t, "de")).toBe("2.3.");
    expect(periodAxisLabel("2026-03-02", "weekly", t, "es")).toBe("2/3");
  });

  it("leaves monthly and yearly ticks alone", () => {
    expect(periodAxisLabel("2026-03-31", "monthly", t, "fr")).toBe("month:03");
    expect(periodAxisLabel("2026-12-31", "yearly", t, "fr")).toBe("2026");
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
