import fs from "fs";
import path from "path";

// w21/217: Log out and Delete account live only in Settings, which sat behind
// the ledger guard, so a user with no usable ledger could not sign out or
// delete their account.
describe("Settings without a ledger", () => {
  const read = (file: string) =>
    fs.readFileSync(path.join(__dirname, "..", file), "utf8");

  it("is not wrapped in the ledger guard", () => {
    const source = read("setting-screen.tsx");
    expect(source.includes("LedgerGuard")).toBe(false);
    expect(source.includes("ledger-guard")).toBe(false);
  });

  it("reads no ledger anywhere it renders", () => {
    for (const file of ["about.tsx", "main-content.tsx"]) {
      expect(read(file).includes("useLedgerGuard")).toBe(false);
    }
  });
});
