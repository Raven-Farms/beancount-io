import fs from "fs";
import path from "path";
import { createTodayWatcher, msUntilNextLocalMidnight } from "../today-watcher";
import { getFormatDate } from "../format-util";
import { toFilterQuery } from "../../screens/transactions-screen/filters/select-filter-query";
import { NO_FILTERS } from "../../screens/transactions-screen/filters/types";

/**
 * w21/078: 1M/3M/YTD captured "today" when applied, so after midnight the
 * journal kept asking for the old window; Accounts, Home and account detail
 * judged price staleness against the day they first rendered.
 */
describe("the today watcher", () => {
  const harness = (start: Date) => {
    let clock = start;
    const days: string[] = [];
    const watcher = createTodayWatcher({
      now: () => clock,
      onDay: (day) => days.push(day),
    });
    return {
      watcher,
      days,
      set: (date: Date) => {
        clock = date;
      },
    };
  };

  it("moves the 1M window's end to the new day on a return after midnight", () => {
    const { watcher, days, set } = harness(new Date(2026, 9, 21, 23, 50));
    const oneMonth = (day: string) =>
      toFilterQuery({ ...NO_FILTERS, range: "1M" }, new Date(`${day}T00:00:00`))
        .time;
    expect(oneMonth(watcher.today())).toBe("2026-09-21 - 2026-10-21");
    set(new Date(2026, 9, 22, 8, 0));
    watcher.onAppStateChange("background");
    expect(days).toEqual([]);
    watcher.onAppStateChange("active");
    expect(days).toEqual(["2026-10-22"]);
    expect(oneMonth(watcher.today())).toBe("2026-09-22 - 2026-10-22");
  });

  it("advances when the midnight timer fires, and only on a new day", () => {
    const { watcher, days, set } = harness(new Date(2026, 9, 21, 12, 0));
    watcher.onMidnight();
    watcher.onAppStateChange("active");
    expect(days).toEqual([]);
    set(new Date(2026, 9, 22, 0, 0, 1));
    watcher.onMidnight();
    expect(days).toEqual(["2026-10-22"]);
  });

  it("times the next local midnight", () => {
    expect(msUntilNextLocalMidnight(new Date(2026, 9, 21, 23, 59, 0))).toBe(
      60_000,
    );
    const midnight = new Date(2026, 9, 22);
    expect(
      getFormatDate(
        new Date(
          new Date(2026, 9, 21, 6).getTime() +
            msUntilNextLocalMidnight(new Date(2026, 9, 21, 6)),
        ),
      ),
    ).toBe(getFormatDate(midnight));
  });

  it("is what the screens that hold today use", () => {
    const read = (...parts: string[]) =>
      fs.readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8");
    const transactions = read(
      "screens",
      "transactions-screen",
      "transactions-screen.tsx",
    );
    expect(transactions.includes("const today = useToday();")).toBe(true);
    expect(transactions.includes("[filters, today],")).toBe(true);
    for (const screen of [
      ["screens", "accounts-screen", "accounts-screen.tsx"],
      ["screens", "home-screen", "home-screen.tsx"],
      ["screens", "account-detail-screen", "account-detail-screen.tsx"],
    ]) {
      const source = read(...screen);
      expect(source.includes("const today = useToday();")).toBe(true);
      expect(
        source.includes("useMemo(() => getFormatDate(new Date()), [])"),
      ).toBe(false);
    }
  });

  it("decides which budget directive is in effect", () => {
    const source = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "..",
        "screens",
        "budget-screen",
        "hooks",
        "use-budget-groups.ts",
      ),
      "utf8",
    );
    expect(source.includes("[data, today],")).toBe(true);
  });
});
