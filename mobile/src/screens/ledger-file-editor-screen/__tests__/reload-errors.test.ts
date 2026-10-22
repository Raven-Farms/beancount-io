import fs from "fs";
import path from "path";

// w21/048: File Changed → Reload swapped in the remote text but kept the old
// error strip — "1 error … line 90" over an 88-line file — until the user left.
// The screen runs queries this runner cannot execute, so the wiring is checked
// on its source; `invalidateLedgerData`'s refetch is tested in common/apollo.
describe("the file editor's Reload", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "index.tsx"),
    "utf8",
  );
  const body = (start: string, end: string) => {
    const from = source.indexOf(start);
    expect(from === -1).toBe(false);
    return source.slice(from, source.indexOf(end, from));
  };

  it("refreshes the errors with the text after a conflict", () => {
    const reload = body(
      "const handleReload = useCallback(",
      "}, [client, refetch, t]);",
    );
    const invalidate = reload.indexOf('invalidateLedgerData(client, "errors")');
    expect(invalidate === -1).toBe(false);
    expect(invalidate < reload.indexOf("await refetch()")).toBe(true);
  });

  it("refreshes the errors from the file-unavailable Reload too", () => {
    const retry = body("const retryLoad = () => {", "};");
    expect(retry.includes('void invalidateLedgerData(client, "errors");')).toBe(
      true,
    );
    expect(retry.includes("void refetch();")).toBe(true);
    const unavailable = body(
      'editorState === "unavailable"',
      "ledgerEditorReload",
    );
    expect(unavailable.includes("onPress={retryLoad}")).toBe(true);
  });

  // w21/446: a failed load had no way forward but leaving the file, and a
  // failed Copy & Reload said nothing and kept the stale sha.
  it("offers Reload on a failed load, not only on an unavailable file", () => {
    const failed = body(
      'editorState === "error"',
      'editorState === "unavailable"',
    );
    expect(failed.includes("onPress={retryLoad}")).toBe(true);
    expect(failed.includes('t("ledgerEditorReload")')).toBe(true);
  });

  it("says a reload failed and leaves the text and the sha alone", () => {
    const reload = body(
      "const handleReload = useCallback(",
      "}, [client, refetch, t]);",
    );
    const failure = reload.indexOf('Alert.alert(t("ledgerEditorLoadFailed"))');
    expect(failure === -1).toBe(false);
    expect(reload.indexOf("await refetch().catch(() => null)") < failure).toBe(
      true,
    );
    // Nothing is swapped in before the guard returns.
    expect(failure < reload.indexOf("shaRef.current = fs")).toBe(true);
    expect(failure < reload.indexOf("setDocumentSpec(")).toBe(true);
  });

  it("plays Copy & Reload's success only when the reload worked", () => {
    const copy = body(
      "const copyThenReload = useCallback(",
      "[handleReload, t]",
    );
    expect(copy.includes("if (await handleReload()) haptics.success();")).toBe(
      true,
    );
  });
});
