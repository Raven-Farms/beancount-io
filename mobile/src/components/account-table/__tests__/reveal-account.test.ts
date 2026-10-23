import fs from "fs";
import path from "path";

/**
 * w21/363: a pending reveal was global and re-opened any ancestor the user
 * collapsed, even after a ledger switch. Source checks: the effect lives in a
 * component that needs the native runtime.
 */
const read = (relative: string) =>
  fs
    .readFileSync(path.join(__dirname, "../../..", relative), "utf8")
    .replace(/\s+/g, "");

describe("the Accounts reveal of a just-opened account", () => {
  it("is stored with the ledger it was opened in", () => {
    expect(
      read("common/vars/reveal-account.ts").includes(
        "makeVar<AccountReveal|null>(null)",
      ),
    ).toBe(true);
    expect(
      read("screens/open-account-screen/open-account-screen.tsx").includes(
        "revealAccountVar({ledgerId,account})",
      ),
    ).toBe(true);
  });

  it("is dropped on a ledger mismatch instead of expanding another tree", () => {
    const src = read("components/account-table/account-table.tsx");
    expect(
      src.includes(
        "if(reveal.ledgerId!==ledgerId){revealAccountVar(null);return;}",
      ),
    ).toBe(true);
  });

  it("opens the ancestors once, so a collapsed row stays collapsed", () => {
    const src = read("components/account-table/account-table.tsx");
    expect(src.includes("if(openedReveal.current!==reveal){")).toBe(true);
    expect(src.includes("openedReveal.current=reveal;")).toBe(true);
    // An opened reveal whose row is hidden again is dropped, not retried.
    expect(src.includes("if(index<0){revealAccountVar(null);return;}")).toBe(
      true,
    );
  });
});
