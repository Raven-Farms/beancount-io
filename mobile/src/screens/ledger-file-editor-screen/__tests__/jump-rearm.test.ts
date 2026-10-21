import fs from "fs";
import path from "path";

/**
 * w21/152: the jump to a link's line re-armed on every focus, so coming back
 * from View errors threw the cursor to the old line and opened the keyboard.
 */
const source = fs
  .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
  .replace(/\s+/gu, "");

describe("the editor's jump to a linked line", () => {
  it("re-arms when a link sets the line, not on every focus", () => {
    expect(source.includes("useFocusEffect(")).toBe(false);
    expect(source.includes("},[initialLineNum,router]);")).toBe(true);
  });

  it("clears the line once taken, so the same link opened again jumps again", () => {
    expect(
      source.includes(
        "setJumpToLine(n);router.setParams({initialLine:undefined});",
      ),
    ).toBe(true);
  });
});
