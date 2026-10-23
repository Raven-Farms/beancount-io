import fs from "fs";
import path from "path";
import { jumpScrollTop } from "../jump-scroll";

// w21/340: tapping an error row with the keyboard up centred the line in the
// editor's full height, behind the accessory bar or inside the keyboard.
describe("jumpScrollTop", () => {
  it("centres a line in the area the keyboard leaves visible", () => {
    // iPhone 17 Pro, banner collapsed: a ~693 pt editor, a ~346 pt inset.
    const top = 2000;
    const withKeyboard = jumpScrollTop(top, 693, 346);
    // The line sits ~173 pt from the top of the scroller, well above the keyboard.
    expect(top - withKeyboard).toBeCloseTo(173.5, 5);
    expect(top - withKeyboard < 693 - 346).toBe(true);
  });

  it("is the old full-height centring when no keyboard is up", () => {
    expect(jumpScrollTop(2000, 693, 0)).toBeCloseTo(2000 - 693 / 2, 5);
  });

  it("never scrolls above the top, and ignores a nonsense inset", () => {
    expect(jumpScrollTop(100, 693, 346)).toBe(0);
    expect(jumpScrollTop(2000, 693, 5000)).toBe(2000);
    expect(jumpScrollTop(2000, 693, -20)).toBeCloseTo(2000 - 693 / 2, 5);
  });
});

describe("the editor's jump", () => {
  const editor = fs
    .readFileSync(path.join(__dirname, "..", "code-editor.tsx"), "utf8")
    .replace(/\s+/gu, "");

  it("scrolls by the keyboard-aware rule, at once and as the layout settles", () => {
    expect(
      editor.includes(
        "v.scrollDOM.scrollTop=jumpScrollTop(data.top,data.clientH,getKeyboardInset(),);",
      ),
    ).toBe(true);
    expect(
      editor.includes("doMeasuredScroll();consttimers=[100,500,1000]"),
    ).toBe(true);
  });

  it("reads the inset when it scrolls, not when the jump starts", () => {
    expect(editor.includes("keyboardInsetRef.current=keyboardInset;")).toBe(
      true,
    );
    expect(editor.split("()=>keyboardInsetRef.current").length - 1).toBe(2);
  });
});
