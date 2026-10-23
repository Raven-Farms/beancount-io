import fs from "fs";
import path from "path";

/**
 * w21/384: the tabs stay mounted across a ledger switch, and the Accounts table
 * and the Reports breakdowns keep their expand/collapse state in component
 * state, so ledger B opened in the layout the user chose on ledger A. Source
 * checks: the screens need the native runtime.
 */
const read = (relative: string) =>
  fs
    .readFileSync(path.join(__dirname, "../../..", relative), "utf8")
    .replace(/\s+/g, "");

describe("trees keyed by ledger", () => {
  it("Accounts remounts its table for another ledger", () => {
    expect(
      read("screens/accounts-screen/accounts-screen.tsx").includes(
        "<AccountTable//Expandandcollapsechoicesbelongtooneledger'stree(w21/384).key={ledgerId}",
      ),
    ).toBe(true);
  });

  it("Reports remounts both breakdowns for another ledger", () => {
    const src = read("screens/reports-screen/reports-screen.tsx");
    const parts = src.split(/<CategoryBreakdown(?!Skeleton)/).slice(1);
    expect(parts.length).toBe(2);
    for (const part of parts) {
      expect(part.slice(0, 200).includes("key={ledgerId}")).toBe(true);
    }
  });
});
