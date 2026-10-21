import fs from "fs";
import path from "path";

/**
 * w21/145: payee suggestions, Account Picker and Browse Ledgers had no
 * keyboard inset, so their last rows stayed under the keyboard and could
 * not be chosen.
 */
const compact = (relative: string) =>
  fs
    .readFileSync(path.join(__dirname, "..", relative), "utf8")
    .replace(/\s+/gu, "");

describe("lists searched with the keyboard up", () => {
  for (const file of [
    "components/text-input-screen/index.tsx",
    "screens/account-picker-screen/account-picker-screen.tsx",
    "screens/ledger-selection/index.tsx",
  ]) {
    it(`${file} insets for the keyboard and dismisses it on drag`, () => {
      const source = compact(file);
      expect(
        source.includes(
          'automaticallyAdjustKeyboardInsets={Platform.OS==="ios"}',
        ),
      ).toBe(true);
      expect(source.includes('keyboardDismissMode="on-drag"')).toBe(true);
    });
  }

  it("drops the picker's fixed padding for the inset", () => {
    expect(
      compact(
        "screens/account-picker-screen/account-picker-screen.tsx",
      ).includes("paddingBottom:150"),
    ).toBe(false);
  });
});
