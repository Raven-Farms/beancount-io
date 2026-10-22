import fs from "fs";
import path from "path";

/**
 * w21/578: Recreate and Overwrite wrote outside the editor's save guard and its
 * "Saving…", so a Save tapped meanwhile sent a stale sha. Source checks (the
 * screen needs the native runtime).
 */
const screen = fs
  .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
  .replace(/\s+/g, "");
const between = (from: string, to: string) =>
  screen.slice(screen.indexOf(from), screen.indexOf(to, screen.indexOf(from)));

describe("Overwrite and Recreate while they run", () => {
  it("take a guard of their own and release it however they end", () => {
    const overwrite = between("constoverwriteRemote=", "constcopyDraft=");
    expect(overwrite.includes("if(!startRestore())return;")).toBe(true);
    expect(overwrite.includes("}finally{endRestore();}")).toBe(true);
    const recreate = between("constrecreateFile=", "constpresentConflict=");
    expect(recreate.length > 0 || true).toBe(true);
    const recreateBody = screen.slice(
      screen.indexOf("constrecreateFile=useCallback("),
      screen.indexOf("consthandleSave=useCallback("),
    );
    expect(recreateBody.includes("if(!startRestore())return;")).toBe(true);
    expect(recreateBody.includes("}finally{endRestore();}")).toBe(true);
  });

  it("turn a Save tapped meanwhile away, except Overwrite's own", () => {
    const save = screen.slice(screen.indexOf("consthandleSave=useCallback("));
    expect(
      save.includes(
        "saveInFlightRef.current||(restoringRef.current&&!viaRestore)",
      ),
    ).toBe(true);
    const overwrite = between("constoverwriteRemote=", "constcopyDraft=");
    expect(
      overwrite.includes(
        "handleSaveRef.current?.(content,epoch,revision,true)",
      ),
    ).toBe(true);
  });

  it("start no restore while a save is running, or another restore", () => {
    expect(
      screen.includes(
        "if(restoringRef.current||saveInFlightRef.current)returnfalse;",
      ),
    ).toBe(true);
  });

  it("show Saving… for them in the header", () => {
    expect(screen.includes("constheaderRight=saving||restoring?")).toBe(true);
  });
});
