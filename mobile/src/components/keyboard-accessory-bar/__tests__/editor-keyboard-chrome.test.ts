import fs from "fs";
import path from "path";

/**
 * Static guardrail: the code editor shows one accessory bar above the keyboard.
 * The editor runs in a WKWebView, which stacks its own form-navigation bar
 * (∧ ∨ ✓) under the app's insert bar unless suppressed. Its ✓ was the only way
 * to hide the keyboard, so the app's bar carries a dismiss button instead.
 */
const SRC = path.join(__dirname, "..", "..", "..");
const compactSource = (file: string) =>
  fs.readFileSync(path.join(SRC, file), "utf8").replace(/\s+/gu, "");

describe("code editor keyboard chrome", () => {
  for (const screen of [
    "screens/ledger-file-editor-screen/index.tsx",
    "screens/edit-transaction-screen/edit-transaction-screen.tsx",
  ]) {
    it(`${screen} hides the web view's accessory bar and wires dismiss`, () => {
      const source = compactSource(screen);
      expect(source.includes("hideKeyboardAccessoryView:true")).toBe(true);
      expect(source.includes("onDismiss={()=>editorRef.current?.blur()}")).toBe(
        true,
      );
    });
  }

  it("dismisses by blurring the editor from the bar's own button", () => {
    expect(
      compactSource("components/code-editor/code-editor.tsx").includes(
        "blur(){viewRef.current?.contentDOM.blur();}",
      ),
    ).toBe(true);
    expect(
      compactSource("components/keyboard-accessory-bar/index.tsx").includes(
        "onPress={onDismiss}",
      ),
    ).toBe(true);
  });

  // w21/144: the bar was shown for Beancount files only, so a README.md or
  // prices.csv had no way to hide the keyboard at all.
  it("gives every writable file the dismiss control and ⇥, shortcuts for .bean only", () => {
    const editor = compactSource("screens/ledger-file-editor-screen/index.tsx");
    expect(
      editor.includes(
        "constshowAccessory=canWrite&&isKeyboardVisible&&initialized;",
      ),
    ).toBe(true);
    expect(editor.includes("shortcuts={beancount}")).toBe(true);
    expect(
      compactSource("components/keyboard-accessory-bar/index.tsx").includes(
        "constbuttons=shortcuts?buildKeyboardShortcutButtons(today,operatingCurrencies):buildPlainTextButtons();",
      ),
    ).toBe(true);
  });
});
