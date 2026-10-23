import fs from "fs";
import path from "path";

// w21/480: with more than 500 budget directives the pages after the first were
// read once. A refetch whose first page came back identical keeps its identity,
// so a pull to refresh or a return to the app never read them again and an
// oldest directive changed elsewhere stayed at its old amount. The hook needs
// the native runtime, so the wiring is checked on its source.
const hook = fs
  .readFileSync(path.join(__dirname, "..", "use-budget-groups.ts"), "utf8")
  .replace(/\s+/g, "");

describe("useBudgetGroups reading the pages after the first", () => {
  it("reads them again on a pull to refresh, whatever the first page did", () => {
    expect(
      hook.includes(
        "if(refreshSignal>0&&ledgerId){setAttempt((current)=>current+1);voidrefetch().catch(()=>undefined);}",
      ),
    ).toBe(true);
  });

  it("reads them again when the ledger revision moves (a return to the app, a write)", () => {
    expect(
      hook.includes("constrevision=useReactiveVar(ledgerRevisionVar);"),
    ).toBe(true);
    expect(
      hook.includes(
        "},[client,ledgerId,firstPage,needsMore,attempt,revision]);",
      ),
    ).toBe(true);
  });

  it("keeps showing the groups while it does", () => {
    // The old pages stay attached to the first page they followed until the new
    // ones land, so a refresh does not blank the panel.
    expect(
      hook.includes("restForPage=rest?.after===firstPage?rest:null;"),
    ).toBe(true);
  });
});
