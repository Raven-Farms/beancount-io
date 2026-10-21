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

// w21/195: leaving the editor during "Saving…" ran the unmount sweep before the
// save set its flag, and nothing swept afterwards: other tabs stayed stale and
// the next delete of the file was refused on a stale sha.
describe("the editor's file sweep after a save", () => {
  it("runs from the save itself once the screen has gone, with no alert", () => {
    expect(source.includes("unmountedRef.current=true;")).toBe(true);
    expect(
      source.includes(
        'voidinvalidateLedgerData(client,"file");returntrue;}voidreportNewErrors(before);',
      ),
    ).toBe(true);
    expect(source.includes("if(unmountedRef.current){")).toBe(true);
  });

  it("still sweeps on unmount for a save that finished while it was open", () => {
    expect(
      source.includes(
        'if(savedThisSessionRef.current){voidinvalidateLedgerData(client,"file");}',
      ),
    ).toBe(true);
  });
});
