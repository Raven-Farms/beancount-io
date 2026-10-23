import fs from "fs";
import path from "path";
import {
  EDITOR_BASE_FONT_PX,
  editorFontSize,
  MAX_EDITOR_FONT_SCALE,
} from "../editor-font";

// w21/341: the editor's 14 px text ignored the system text size on iOS, at AX2
// too, where native body text is about 33 pt.
describe("editorFontSize", () => {
  it("is 14 px at the default size", () => {
    expect(editorFontSize(1)).toBe(EDITOR_BASE_FONT_PX);
    expect(editorFontSize(undefined)).toBe(14);
    expect(editorFontSize(Number.NaN)).toBe(14);
  });

  it("grows with the system text size", () => {
    expect(editorFontSize(1.3)).toBe(18);
    expect(editorFontSize(2) > editorFontSize(1.3)).toBe(true);
  });

  it("is visibly larger at AX2, within a cap", () => {
    // AX2 is about 2.35 on iOS: well above 14 px, and under the cap.
    expect(editorFontSize(2.35)).toBe(33);
    expect(editorFontSize(2.35) > EDITOR_BASE_FONT_PX * 2).toBe(true);
    expect(editorFontSize(10)).toBe(
      Math.round(EDITOR_BASE_FONT_PX * MAX_EDITOR_FONT_SCALE),
    );
  });

  it("never goes below the default for a small scale", () => {
    expect(editorFontSize(0.8)).toBe(14);
  });
});

describe("the editor takes the scale as a prop", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", "..", "..", ...parts), "utf8")
      .replace(/\s+/gu, "");

  it("sizes the code and gutter from it and reconfigures when it changes", () => {
    const editor = read("components", "code-editor", "code-editor.tsx");
    expect(editor.includes("fontSize:`${fontSize}px`,lineHeight:")).toBe(true);
    expect(editor.includes('".cm-gutters":{fontSize:`${fontSize}px`,')).toBe(
      true,
    );
    expect(editor.includes("constfontSize=editorFontSize(fontScale);")).toBe(
      true,
    );
    expect(editor.includes("appliedFontSizeRef.current===fontSize")).toBe(true);
    expect(editor.includes("},[editorTheme,fontSize]);")).toBe(true);
  });

  it("is passed by both screens that mount the editor", () => {
    expect(
      read("screens", "ledger-file-editor-screen", "index.tsx").includes(
        "fontScale={fontScale}",
      ),
    ).toBe(true);
    expect(
      read(
        "screens",
        "edit-transaction-screen",
        "edit-transaction-screen.tsx",
      ).includes("fontScale={fontScale}"),
    ).toBe(true);
  });
});
