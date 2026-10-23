import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

// w21/295: a ledger list that failed to load read "No ledger selected" with
// Create and Discover, inviting a duplicate ledger on a flaky sign-in. The
// guard uses hooks this runner cannot execute, so the wiring is checked on its
// source.
describe("the ledger guard when the ledger list fails", () => {
  const source = fs
    .readFileSync(path.join(__dirname, "..", "ledger-guard.tsx"), "utf8")
    .replace(/\s+/g, "");

  it("reads the query's error and refetch", () => {
    expect(
      source.includes(
        "const{data,loading,error,refetch}=useListLedgersQuery({skip:!!ledgerId,});",
      ),
    ).toBe(true);
  });

  it("shows the failure with Retry before the empty state, only with no data", () => {
    const failure = source.indexOf("if(error&&!data){");
    const empty = source.indexOf('t("ledgerGuardTitle")');
    expect(failure === -1 || empty === -1).toBe(false);
    expect(failure < empty).toBe(true);
    const block = source.slice(failure, empty);
    expect(block.includes('t("discoveryLoadError")')).toBe(true);
    expect(block.includes("refetch().catch(()=>undefined)")).toBe(true);
    expect(block.includes("create-ledger")).toBe(false);
    expect(en.discoveryLoadError).toBe(
      "Couldn’t load ledgers. Please try again.",
    );
  });
});
