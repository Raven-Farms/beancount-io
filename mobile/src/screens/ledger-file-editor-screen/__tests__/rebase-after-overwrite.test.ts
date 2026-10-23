import fs from "fs";
import path from "path";
import { createEditorRecovery } from "../../../components/code-editor/editor-recovery";

/**
 * w21/522: Overwrite and Recreate save outside the editor's own save, so its
 * saved-text baseline stayed at the text first loaded and a revert read as no
 * change. Source checks (the screen needs the native runtime), with the
 * recovery's `latest()` the screen reads to keep what was typed meanwhile.
 */
const screen = fs
  .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
  .replace(/\s+/g, "");
const body = (from: string, to: string) =>
  screen.slice(screen.indexOf(from), screen.indexOf(to, screen.indexOf(from)));

describe("after Overwrite or Recreate succeeds", () => {
  it("hands the editor the text it had against the text just saved", () => {
    const rebase = body("constrebaseOnSaved", "constoverwriteRemote");
    expect(
      rebase.includes("setDocumentSpec({value:latest,epoch,savedValue:saved})"),
    ).toBe(true);
    expect(
      rebase.includes("resetRevisionTracker(revisionTrackerRef.current)"),
    ).toBe(true);
    expect(rebase.includes("setHasUnsavedChanges(latest!==saved)")).toBe(true);
  });

  it("is done by Overwrite once its save succeeds", () => {
    const overwrite = body(
      "constoverwriteRemote=",
      "[rebaseOnSaved,refetch,t],",
    );
    const latest = overwrite.indexOf(
      "constlatest=recoveryRef.current.latest()",
    );
    const save = overwrite.indexOf(
      "handleSaveRef.current?.(content,epoch,revision,true)",
    );
    expect(latest > -1 && latest < save).toBe(true);
    expect(overwrite.includes("rebaseOnSaved(latest,content)")).toBe(true);
  });

  it("is done by Recreate once the file is created", () => {
    const recreate = body("constrecreateFile=", "consthandleSave=");
    expect(recreate.includes("constlatest=recoveryRef.current.latest()")).toBe(
      true,
    );
    expect(recreate.includes("rebaseOnSaved(latest,content)")).toBe(true);
  });
});

describe("the recovery's latest text", () => {
  it("follows the editor's drafts and a save", () => {
    const recovery = createEditorRecovery();
    recovery.loaded("a");
    expect(recovery.latest()).toBe("a");
    recovery.draft("ab");
    expect(recovery.latest()).toBe("ab");
    recovery.saved("abc");
    expect(recovery.latest()).toBe("abc");
  });
});
