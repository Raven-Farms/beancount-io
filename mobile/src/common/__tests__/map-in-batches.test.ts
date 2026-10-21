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
    expect(hook.includes("mapInBatches(groups, BUDGET_PANEL_BATCH,")).toBe(
      true,
    );
    expect(hook.includes("groups.slice(0,")).toBe(false);
  });
});
