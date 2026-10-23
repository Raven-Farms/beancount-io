import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";
import { nameFailureKey } from "../profile-changes";

// w21/288: changing the username and the name together said "Failed to save"
// when only the name write failed, after the username (and every ledger id)
// had already changed. The screen runs hooks this runner cannot execute, so the
// wiring is checked on its source.
describe("a failed name write after the username saved", () => {
  it("says the username was saved", () => {
    expect(nameFailureKey(true)).toBe("profilePartialSave");
    expect(nameFailureKey(false)).toBe("saveFailed");
    expect(en.profilePartialSave).toBe(
      "Username saved, but your name couldn't be saved. Try again.",
    );
  });

  const source = fs
    .readFileSync(path.join(__dirname, "..", "profile-screen.tsx"), "utf8")
    .replace(/\s+/g, "");

  it("picks the message from whether the username was saved", () => {
    expect(
      source.includes(
        "message:t(nameFailureKey(savedUsernameRef.current!==null))",
      ),
    ).toBe(true);
  });

  it("does not send the saved username again on a retry", () => {
    expect(
      source.includes(
        "pending.username!==undefined&&pending.username!==savedUsernameRef.current",
      ),
    ).toBe(true);
    // Recorded as soon as the write lands, before the ledgers are renamed.
    expect(
      source.indexOf("savedUsernameRef.current=pending.username") <
        source.indexOf("renameLedgerOwner("),
    ).toBe(true);
  });
});
