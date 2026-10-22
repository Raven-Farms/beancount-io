import fs from "fs";
import path from "path";
import { readBudgetPages } from "../read-budget-pages";

// w21/397: the Budget page and Home asked for one page of 500 directives and never
// looked at `total`, so a heavy user's oldest budget card disappeared.
describe("readBudgetPages", () => {
  const ledger = Array.from({ length: 1203 }, (_, i) => ({ id: i }));
  const reader = (calls: number[]) => async (offset: number) => {
    calls.push(offset);
    return ledger.slice(offset, offset + 500);
  };

  it("reads every page after the first until the total", async () => {
    const calls: number[] = [];
    const rest = await readBudgetPages(500, 1203, 500, reader(calls));
    expect(calls).toEqual([500, 1000]);
    expect(rest.length).toBe(703);
    expect((rest[rest.length - 1] as { id: number }).id).toBe(1202);
  });

  it("reads one extra page for 501 directives, and none when the first page was all", async () => {
    const calls: number[] = [];
    const small = ledger.slice(0, 501);
    const rest = await readBudgetPages(500, 501, 500, async (offset) => {
      calls.push(offset);
      return small.slice(offset, offset + 500);
    });
    expect(calls).toEqual([500]);
    expect(rest.length).toBe(1);
    const none: number[] = [];
    expect(await readBudgetPages(500, 500, 500, reader(none))).toEqual([]);
    expect(none).toEqual([]);
  });

  it("fails rather than return a partial set when a page comes back empty", async () => {
    let failed = false;
    try {
      await readBudgetPages(500, 1203, 500, async () => []);
    } catch {
      failed = true;
    }
    expect(failed).toBe(true);
  });

  it("is what the hook reads the rest with, and groups wait for every page", () => {
    const hook = fs
      .readFileSync(path.join(__dirname, "..", "use-budget-groups.ts"), "utf8")
      .replace(/\s+/g, "");
    expect(
      hook.includes(
        "awaitreadBudgetPages(firstPage.data.length,firstPage.total,",
      ),
    ).toBe(true);
    expect(
      hook.includes(
        "(complete&&firstPage?[...firstPage.data,...(restForPage?.data??[])]:[])",
      ),
    ).toBe(true);
    expect(hook.includes("loaded:complete,")).toBe(true);
  });
});
