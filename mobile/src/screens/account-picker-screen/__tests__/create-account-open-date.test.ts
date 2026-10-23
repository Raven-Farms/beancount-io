import fs from "fs";
import path from "path";

/**
 * The hop the unit runner cannot render: New Transaction passes its date to
 * the picker, the picker's Create row hands it to Open Account, and Open
 * Account starts on it (w21/008).
 */
const read = (...parts: string[]) =>
  fs.readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8");

describe("Create account from a dated entry", () => {
  it("passes the entry date from New Transaction through to Open Account", () => {
    expect(
      read(
        "multi-postings-transaction",
        "multi-postings-transaction-screen.tsx",
      ).includes("entryDate: date,"),
    ).toBe(true);
    expect(
      read("account-picker-screen", "account-picker-screen.tsx").includes(
        "openDate: entryDate,",
      ),
    ).toBe(true);
    expect(
      read("open-account-screen", "open-account-screen.tsx").includes(
        "initialOpenDate(openDate, new Date())",
      ),
    ).toBe(true);
  });
});
