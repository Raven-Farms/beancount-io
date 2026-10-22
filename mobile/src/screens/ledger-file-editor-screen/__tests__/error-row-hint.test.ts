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
        'accessibilityHint={err.lineno!=null?t("ledgerEditorJumpToLine",{line:err.lineno}):undefined}',
      ),
    ).toBe(true);
    expect(en.ledgerEditorJumpToLine).toBe("Jump to line {{line}}");
  });

  it("are inert when they have no line", () => {
    expect(source.includes("disabled={err.lineno==null}")).toBe(true);
  });
});
