import fs from "fs";
import path from "path";

// w21/630: with the ledger's metadata failing to load, Done stayed grey with no
// message. The screen needs the native runtime, so the wiring is checked on
// source.
const screen = fs
  .readFileSync(path.join(__dirname, "..", "open-account-screen.tsx"), "utf8")
  .replace(/\s+/g, "");

describe("Open Account when the ledger's metadata fails to load", () => {
  it("reads the failure and a way to read again", () => {
    expect(
      screen.includes(
        "const{data:meta,currencies,error:metaError,refetch:refetchMeta,}=useLedgerMeta(userId,ledgerId);",
      ),
    ).toBe(true);
  });

  it("shows the load failure with Retry only while nothing has loaded", () => {
    expect(
      screen.includes(
        "meta===undefined&&metaError?(<CardLoadFailureonRetry={()=>voidrefetchMeta().catch(()=>{})}/>):null",
      ),
    ).toBe(true);
  });
});
