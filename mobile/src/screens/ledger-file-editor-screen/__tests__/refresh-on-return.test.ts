import fs from "fs";
import path from "path";

/**
 * w21/544: View errors opens Notifications, whose error row opens a second
 * editor on the same file. Fixing the error there left the first editor's copy
 * outdated, and a save from it hit the conflict. Source checks (the screen
 * needs the native runtime).
 */
const screen = fs
  .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
  .replace(/\s+/g, "");
const effect = screen.slice(
  screen.indexOf("useFocusEffect(useCallback(()=>{if(!initialized)"),
  screen.indexOf("consthandleEdit=useCallback("),
);

describe("returning to an editor whose file was saved elsewhere", () => {
  it("re-reads the file on a later focus, not the first", () => {
    expect(effect.length > 0).toBe(true);
    expect(
      effect.includes("focusedBeforeRef.current=true;returnundefined;"),
    ).toBe(true);
    expect(effect.includes("refetch()")).toBe(true);
  });

  it("swaps the remote text in only when its sha moved", () => {
    expect(effect.includes("file.sha===shaRef.current")).toBe(true);
    expect(effect.includes("applyRemoteFile(file)")).toBe(true);
  });

  it("leaves unsaved edits and a running save alone, before and after the read", () => {
    const guard = "unsavedRef.current||saveInFlightRef.current";
    expect(effect.split(guard).length - 1).toBe(2);
  });

  it("shares the swap with Reload, so both refresh the same state", () => {
    expect(screen.includes("applyRemoteFile(result.data.getLedgerFile)")).toBe(
      true,
    );
  });

  it("returns to an existing Notifications instead of stacking another", () => {
    expect(screen.includes('router.navigate("/(app)/notifications")')).toBe(
      true,
    );
    expect(screen.includes('router.push("/(app)/notifications")')).toBe(false);
  });
});
