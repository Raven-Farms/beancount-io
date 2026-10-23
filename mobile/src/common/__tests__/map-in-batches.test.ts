import fs from "fs";
import path from "path";
import { mapInBatches } from "../map-in-batches";

// w21/165: Home's budget panel priced only the first twelve budgets
// alphabetically, so a 250% budget later in the alphabet never showed.
describe("mapInBatches", () => {
  it("maps every item, in order, with at most `size` in flight", async () => {
    let inFlight = 0;
    let peak = 0;
    const items = Array.from({ length: 13 }, (_, index) => index);
    const results = await mapInBatches(items, 12, async (item) => {
      inFlight += 1;
      peak = Math.max(peak, inFlight);
      await new Promise((resolve) => setTimeout(resolve, 1));
      inFlight -= 1;
      return item * 2;
    });
    expect(results).toEqual(items.map((item) => item * 2));
    expect(peak).toBe(12);
  });

  it("is how the budget panel prices every budget before ranking", () => {
    const hook = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "..",
        "screens",
        "home-screen",
        "hooks",
        "use-budget-panel.ts",
      ),
      "utf8",
    );
    expect(
      hook
        .replace(/\s+/gu, "")
        .includes("mapInBatches(groups,BUDGET_PANEL_BATCH,"),
    ).toBe(true);
    expect(hook.includes("groups.slice(0,")).toBe(false);
  });

  // w21/336: a superseded run (another ledger, a write) kept firing every
  // remaining read.
  it("starts no further batch once cancelled, and keeps what it has", async () => {
    const started: number[] = [];
    let stop = false;
    const items = Array.from({ length: 30 }, (_, index) => index);
    const results = await mapInBatches(
      items,
      12,
      async (item) => {
        started.push(item);
        // The user switches ledger while the first batch is in flight.
        stop = true;
        return item;
      },
      () => stop,
    );
    expect(started.length).toBe(12);
    expect(results).toEqual(items.slice(0, 12));
  });

  it("runs every batch when it is never cancelled, as before", async () => {
    const results = await mapInBatches(
      [1, 2, 3],
      2,
      async (n) => n,
      () => false,
    );
    expect(results).toEqual([1, 2, 3]);
  });

  it("is told by the panel's cleanup", () => {
    const hook = fs
      .readFileSync(
        path.join(
          __dirname,
          "..",
          "..",
          "screens",
          "home-screen",
          "hooks",
          "use-budget-panel.ts",
        ),
        "utf8",
      )
      .replace(/\s+/gu, "");
    expect(hook.includes("()=>cancelled,),).then((results)=>{")).toBe(true);
  });
});
