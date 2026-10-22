import fs from "fs";
import path from "path";
import { renameLedgerKeys, renamedLedgerId } from "../ledger-owner-rename";

// w21/226: renaming the account renames the owner of every ledger it holds, and
// the app kept its selection, Recent accounts and merchant marks on the old ids.
describe("renamedLedgerId", () => {
  it("moves a ledger the renamed account owns", () => {
    expect(renamedLedgerId("alice/home", "alice", "alice2")).toBe(
      "alice2/home",
    );
    expect(renamedLedgerId("alice/a/b", "alice", "alice2")).toBe("alice2/a/b");
  });

  it("leaves a shared ledger, a lookalike owner and an unset owner alone", () => {
    expect(renamedLedgerId("bob/home", "alice", "alice2")).toBe("bob/home");
    expect(renamedLedgerId("alice-co/home", "alice", "alice2")).toBe(
      "alice-co/home",
    );
    expect(renamedLedgerId("alice", "alice", "alice2")).toBe("alice");
    expect(renamedLedgerId("alice/home", "", "x")).toBe("alice/home");
  });
});

describe("renameLedgerKeys", () => {
  it("re-keys per-ledger state and keeps every value", () => {
    const usage = {
      "alice/home": { "Expenses:Food": { count: 3 } },
      "bob/shared": { "Expenses:Fun": { count: 1 } },
    };
    expect(renameLedgerKeys(usage, "alice", "alice2")).toEqual({
      "alice2/home": { "Expenses:Food": { count: 3 } },
      "bob/shared": { "Expenses:Fun": { count: 1 } },
    });
  });

  it("returns a record unchanged when nothing is owned by the old name", () => {
    expect(renameLedgerKeys({ "bob/x": 1 }, "alice", "alice2")).toEqual({
      "bob/x": 1,
    });
    expect(renameLedgerKeys({}, "alice", "alice2")).toEqual({});
  });
});

describe("the Profile save", () => {
  it("follows the renamed ledgers with everything remembered per ledger", () => {
    const profile = fs
      .readFileSync(
        path.join(
          __dirname,
          "..",
          "..",
          "screens",
          "profile",
          "profile-screen.tsx",
        ),
        "utf8",
      )
      .replace(/\s+/g, "");
    const rename = profile.indexOf(
      "renameLedgerOwner(savedValues.username,pending.username);",
    );
    expect(rename > -1).toBe(true);
    // After the rename succeeded, before the directory is re-listed.
    expect(profile.indexOf("awaitupdateUsername(") < rename).toBe(true);
    expect(rename < profile.indexOf("refreshLedgers()")).toBe(true);
    expect(profile.includes('invalidateLedgerData(client,"file")')).toBe(true);

    const state = fs
      .readFileSync(
        path.join(__dirname, "..", "vars", "rename-ledger-owner.ts"),
        "utf8",
      )
      .replace(/\s+/g, "");
    for (const piece of [
      "ledgerVar(renamedLedgerId(selected,oldOwner,newOwner))",
      "accountUsageVar(renameLedgerKeys(accountUsageVar()",
      "merchantRecurringOverridesVar(renameLedgerKeys(merchantRecurringOverridesVar()",
    ]) {
      expect(state.includes(piece)).toBe(true);
    }
  });
});
