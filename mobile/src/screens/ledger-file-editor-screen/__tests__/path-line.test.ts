import fs from "fs";
import path from "path";
import { editorPathLine } from "../utils";

// w21/590: the header shows the file name only, so `books/2025/jan.bean` and
// `books/2026/jan.bean` looked the same before saving.
describe("the editor's path line", () => {
  it("tells two same-named files apart", () => {
    expect(editorPathLine("books/2025/jan.bean")).toBe("books/2025/jan.bean");
    expect(editorPathLine("books/2026/jan.bean")).not.toBe(
      editorPathLine("books/2025/jan.bean"),
    );
  });

  it("is absent for a file at the root, where the name says it all", () => {
    expect(editorPathLine("main.bean")).toBe(null);
  });

  it("is drawn under the header, truncated in the middle", () => {
    const screen = fs
      .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
      .replace(/\s+/g, "");
    expect(
      screen.includes(
        "{editorPathLine(path)?(<Texttest" +
          'ID="ledger-editor-path"style={styles.pathLine}numberOfLines={1}ellipsizeMode="middle">',
      ),
    ).toBe(true);
  });
});
