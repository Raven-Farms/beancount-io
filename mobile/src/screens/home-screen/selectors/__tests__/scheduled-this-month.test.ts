import fs from "fs";
import path from "path";
import {
  hasScheduledRows,
  monthToDateWindow,
  scheduledThisMonthBql,
  withMonthToDate,
} from "../scheduled-this-month";
import { selectSpendingCompare } from "../select-spending-compare";

// w21/337: Home read this month over a window that holds for the whole month,
// so a bill pre-entered for the 30th counted as spent on the 21st: the budget
// panel said "Above target" where the Budget page read $0.00, and Spending's
// "This month" included an unpaid bill.
describe("scheduled entries this month", () => {
  it("asks for anything dated after today and within the month", () => {
    expect(scheduledThisMonthBql("2026-10-21")).toBe(
      "SELECT date WHERE date > 2026-10-21 AND date <= 2026-10-31 LIMIT 1",
    );
    // A short month, and a leap one.
    expect(scheduledThisMonthBql("2026-02-03").includes("<= 2026-02-28")).toBe(
      true,
    );
    expect(scheduledThisMonthBql("2028-02-03").includes("<= 2028-02-29")).toBe(
      true,
    );
  });

  it("reads one row as scheduled, none or a failure as not", () => {
    expect(hasScheduledRows({ rows: [["2026-10-30"]] })).toBe(true);
    expect(hasScheduledRows({ rows: [] })).toBe(false);
    expect(hasScheduledRows(null)).toBe(false);
    expect(hasScheduledRows(undefined)).toBe(false);
  });

  it("names this month, first day to today", () => {
    expect(monthToDateWindow("2026-10-21")).toBe("2026-10-01 - 2026-10-21");
  });
});

describe("Spending's This month with a bill pre-entered for later", () => {
  const month = (date: string, usd: string) => ({
    date,
    balance: { USD: usd },
  });
  const today = "2026-10-21";
  const reference = new Date(2026, 9, 21);

  it("counts only what has happened, once this month is read to today", () => {
    // The month-long window: last month 120, this month 400 (the Oct 30 bill).
    const window = [month("2026-09-30", "120"), month("2026-10-31", "400")];
    const before = selectSpendingCompare(window, "USD", reference);
    expect(before.thisMonth).toBe(400);
    const toToday = [month("2026-10-21", "0")];
    const after = selectSpendingCompare(
      withMonthToDate(window, toToday, today),
      "USD",
      reference,
    );
    expect(after.thisMonth).toBe(0);
    expect(after.lastMonth).toBe(120);
  });

  it("keeps the month window until the to-today read lands", () => {
    const window = [month("2026-09-30", "120"), month("2026-10-31", "400")];
    expect(withMonthToDate(window, undefined, today)).toEqual(window);
  });
});

describe("Home's wiring", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8")
      .replace(/\s+/gu, "");

  it("reads this month to today in the Spending card only when entries are scheduled", () => {
    const card = read("components", "spending-card.tsx");
    expect(
      card.includes(
        "const{scheduled,refetch:refetchScheduled}=useScheduledThisMonth(ledgerId,today,Boolean(guest),);",
      ),
    ).toBe(true);
    expect(card.includes("skip:!ledgerId||!contextSettled||!scheduled,")).toBe(
      true,
    );
    expect(
      card.includes(
        "scheduled?toToday.data?.getLedgerIntervalTotals:undefined",
      ),
    ).toBe(true);
  });

  // w21/470: a pull to refresh left the to-today read and the check on cache.
  it("asks for the month, the check and the to-today read again on a pull to refresh", () => {
    const card = read("components", "spending-card.tsx");
    const effect = card.slice(card.indexOf("if(refreshSignal>0&&ledgerId){"));
    const body = effect.slice(
      0,
      effect.indexOf("},[refreshSignal,ledgerId]);"),
    );
    expect(body.includes("voidrefetch().catch(()=>undefined);")).toBe(true);
    expect(body.includes("voidrefetchScheduled().catch(()=>undefined);")).toBe(
      true,
    );
    expect(
      body.includes("if(scheduled)voidtoToday.refetch().catch(()=>undefined);"),
    ).toBe(true);
    // After the queries it refetches exist.
    expect(
      card.indexOf("if(refreshSignal>0&&ledgerId){") >
        card.indexOf("consttoToday=useGetLedgerIntervalTotalsQuery("),
    ).toBe(true);
  });

  it("reads the panel's period to today when they are, else keeps the stable window", () => {
    const hook = read("hooks", "use-budget-panel.ts");
    expect(hook.includes("scheduledThisMonthBql(today)")).toBe(true);
    expect(
      hook.includes(
        'scheduled?totals("network-only",toToday).catch(()=>null):Promise.resolve(null)',
      ),
    ).toBe(true);
    // The stable window is still the fallback and the cache.
    expect(hook.includes('read??totals("network-only")')).toBe(true);
    expect(hook.includes('.catch(()=>totals("cache-only"))')).toBe(true);
  });
});
