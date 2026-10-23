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

  // w21/319: the multiline layout's KeyboardAvoidingView already shrinks the
  // list by the keyboard, so the scroll view must not inset for it again.
  it("insets the suggestions only where nothing else avoids the keyboard", () => {
    const source = compact("components/text-input-screen/index.tsx");
    expect(
      source.includes(
        'automaticallyAdjustKeyboardInsets={Platform.OS==="ios"&&!multiline}',
      ),
    ).toBe(true);
    expect(source.includes('keyboardDismissMode="on-drag"')).toBe(true);
    expect(
      source.includes('behavior={Platform.OS==="ios"?"padding":undefined}'),
    ).toBe(true);
  });

  it("drops the picker's fixed padding for the inset", () => {
    expect(
      compact(
        "screens/account-picker-screen/account-picker-screen.tsx",
      ).includes("paddingBottom:150"),
    ).toBe(false);
  });

  // w21/146: the New Transaction form under the number pad.
  it("lets New Transaction scroll its postings and Remainder above the pad", () => {
    const source = compact(
      "screens/multi-postings-transaction/multi-postings-transaction-screen.tsx",
    );
    expect(
      source.includes(
        'automaticallyAdjustKeyboardInsets={Platform.OS==="ios"}',
      ),
    ).toBe(true);
    expect(source.includes('keyboardDismissMode="interactive"')).toBe(true);
  });
});
