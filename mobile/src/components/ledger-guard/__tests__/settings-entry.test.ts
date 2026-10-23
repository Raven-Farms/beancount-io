import fs from "fs";
import path from "path";

/**
 * w21/375: Settings, with Log out and Delete Account, was reachable only from
 * the drawer, whose button sits inside the guard, so a signed-in user with no
 * ledger had no way there. Source check: the guard needs hooks this runner
 * cannot execute.
 */
const source = fs
  .readFileSync(path.join(__dirname, "..", "ledger-guard.tsx"), "utf8")
  .replace(/\s+/g, "");

describe("the ledger guard's way to Settings", () => {
  const button =
    'testID="ledger-guard-settings"style={[styles.button,styles.buttonSecondary]}onPress={()=>{router.push("/(app)/settings");}}';

  it("is on every state that replaces the tabs", () => {
    expect(source.split(button).length - 1).toBe(3);
    const failure = source.indexOf('testID="ledger-guard-load-error"');
    const empty = source.indexOf('t("ledgerGuardTitle")');
    const gone = source.indexOf('testID="ledger-guard-gone"');
    const settings = (from: number, to: number) =>
      source.slice(from, to).includes('testID="ledger-guard-settings"');
    expect(settings(failure, empty)).toBe(true);
    expect(settings(empty, gone)).toBe(true);
    expect(settings(gone, source.length)).toBe(true);
  });

  it("is named Settings", () => {
    expect(source.includes('accessibilityLabel={t("settings")}')).toBe(true);
  });
});
