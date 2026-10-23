import fs from "fs";
import path from "path";
import { translationLocales } from "../../../translations/__tests__/locale-parity";

/**
 * w21/579: Create Ledger finishing after the user went Back still switched the
 * ledger and popped every screen to the tabs, under whatever they had opened
 * meanwhile. Source checks (the screen needs the native runtime).
 */
const screen = fs
  .readFileSync(path.join(__dirname, "..", "create-ledger-screen.tsx"), "utf8")
  .replace(/\s+/g, "");

describe("a Create that lands after the user left", () => {
  it("only toasts, before it switches the ledger or navigates", () => {
    const landed = screen.slice(
      screen.indexOf("awaitrefresh(result.data!.createLedger)"),
    );
    const guard = landed.indexOf("if(!isHere()){");
    expect(guard > -1).toBe(true);
    expect(guard < landed.indexOf("ledgerVar(id);")).toBe(true);
    expect(guard < landed.indexOf('router.dismissTo("/(app)/(tabs)")')).toBe(
      true,
    );
    const branch = landed.slice(guard, landed.indexOf("ledgerVar(id);"));
    expect(branch.includes('t("createLedgerCreated",{name:id})')).toBe(true);
    expect(branch.includes("return;")).toBe(true);
    expect(branch.includes("ledgerVar(")).toBe(false);
  });

  it("is worded in every language", () => {
    for (const locale of translationLocales()) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const catalog = require(`../../../translations/${locale}`)[locale];
      expect(catalog.createLedgerCreated.includes("{{name}}")).toBe(true);
    }
  });
});
