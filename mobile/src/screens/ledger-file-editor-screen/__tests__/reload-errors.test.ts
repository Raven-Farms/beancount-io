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
      "}, [client, refetch]);",
    );
    const invalidate = reload.indexOf('invalidateLedgerData(client, "errors")');
    expect(invalidate === -1).toBe(false);
    expect(invalidate < reload.indexOf("await refetch()")).toBe(true);
  });

  it("refreshes the errors from the file-unavailable Reload too", () => {
    const unavailable = body(
      'editorState === "unavailable"',
      "ledgerEditorReload",
    );
    expect(
      unavailable.includes('void invalidateLedgerData(client, "errors");'),
    ).toBe(true);
  });
});
