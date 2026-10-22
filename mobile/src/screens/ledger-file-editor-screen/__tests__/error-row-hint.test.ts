import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

// w21/276 (the button roles landed in w21/141): an error row that jumps to its
// line says where, and a row with no line is not tappable.
describe("the file editor's error rows", () => {
  const source = fs
    .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
    .replace(/\s+/g, "");

  it("hint where a tap goes", () => {
    expect(
      source.includes(
        'accessibilityHint={t("ledgerEditorJumpToLine",{line:err.lineno,})}',
      ),
    ).toBe(true);
    expect(en.ledgerEditorJumpToLine).toBe("Jump to line {{line}}");
  });

  // w21/428: a disabled touchable is read as "dimmed"; a row with no line is
  // plain text instead.
  it("are plain text when they have no line, not a disabled button", () => {
    expect(source.includes("disabled={err.lineno")).toBe(false);
    expect(source.includes("{err.lineno!=null?(<TouchableOpacity")).toBe(true);
    expect(
      source.includes(
        'accessibilityRole="text"accessibilityLabel={errorMessageWithHint(err)}',
      ),
    ).toBe(true);
  });
});
