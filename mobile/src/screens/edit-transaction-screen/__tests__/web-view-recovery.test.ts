import fs from "fs";
import path from "path";

// w21/621: iOS killing the editor's web view reset Edit Transaction to the
// original slice and re-applied the last shortcut at the top, as the file
// editor did before w21/342. The screen needs the native runtime, so the
// wiring is checked on source; the recovery rules are in editor-recovery.test.
const screen = fs
  .readFileSync(
    path.join(__dirname, "..", "edit-transaction-screen.tsx"),
    "utf8",
  )
  .replace(/\s+/g, "");

describe("Edit Transaction after the editor's web view is killed", () => {
  it("hands the editor the ready and draft callbacks", () => {
    expect(screen.includes("onReady={handleEditorReady}")).toBe(true);
    expect(screen.includes("onDraft={handleDraft}")).toBe(true);
  });

  it("keeps the loaded slice and the saved text for the recovery", () => {
    expect(screen.includes("recoveryRef.current.loaded(context.slice);")).toBe(
      true,
    );
    expect(screen.includes("recoveryRef.current.saved(content);")).toBe(true);
  });

  it("re-seeds the draft under a new epoch and drops the stale insert", () => {
    expect(
      screen.includes(
        "constplan=recoveryRef.current.ready();if(!plan)return;constepoch=documentEpochRef.current+1;documentEpochRef.current=epoch;resetRevisionTracker(revisionTrackerRef.current);setDocumentSpec({value:plan.value,epoch,savedValue:plan.savedValue,});setInsertSpec(null);",
      ),
    ).toBe(true);
  });

  it("spends an insert once the editor has made the edit", () => {
    expect(
      screen.includes(
        "setHasUnsavedChanges(dirty);setSaveError(null);//Theeditorhasmadetheedit,sotheinsertthataskedforitisspent.setInsertSpec(null);",
      ),
    ).toBe(true);
  });
});
