import fs from "fs";
import path from "path";

// w21/577: the chart's "Try again" refetched the context and the report but not
// the journal, whose "Failed to load journal" has no retry of its own. Source
// check (the screen needs the native runtime).
const screen = fs
  .readFileSync(path.join(__dirname, "..", "account-detail-screen.tsx"), "utf8")
  .replace(/\s+/g, "");

describe("the account detail chart's Try again", () => {
  it("also re-reads the journal, so one tap recovers the whole screen", () => {
    const retry = screen.slice(screen.indexOf("constretryChart=useCallback("));
    const body = retry.slice(0, retry.indexOf("},["));
    expect(body.includes("ledgerMetaRefetch()")).toBe(true);
    expect(body.includes("unitsReportRefetch()")).toBe(true);
    expect(body.includes("voidjournalRefetch().catch(()=>undefined);")).toBe(
      true,
    );
  });

  it("lists the journal's refetch among the callback's inputs", () => {
    const retry = screen.slice(screen.indexOf("constretryChart=useCallback("));
    const deps = retry.slice(retry.indexOf("},[") + 3, retry.indexOf("]);"));
    expect(deps.includes("journalRefetch")).toBe(true);
  });
});
