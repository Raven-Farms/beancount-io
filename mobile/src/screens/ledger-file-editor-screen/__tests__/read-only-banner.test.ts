import fs from "fs";
import path from "path";

/**
 * Static guardrail: the file editor says when a ledger is read-only. It used
 * to drop the Save button and nothing else, while taps still moved the active
 * line, so nothing explained why the keyboard never came.
 */
describe("file editor read-only indicator", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "index.tsx"),
    "utf8",
  );

  it("shows the translated read-only message when the ledger cannot be written", () => {
    const start = source.indexOf("{!canWrite &&");
    expect(start === -1).toBe(false);
    const banner = source.slice(start, source.indexOf(") : null}", start));
    // A file that is not UTF-8 says so, even beside the error banner
    // (w21/042); a read-only ledger keeps its own message.
    expect(banner.includes("(lossy || fileErrors.length === 0)")).toBe(true);
    expect(
      banner.includes('t(lossy ? "ledgerEditorNotUtf8" : "ledgerReadOnly")'),
    ).toBe(true);
  });

  it("still hides Save on a read-only ledger", () => {
    expect(
      source.includes("headerRight: canWrite ? headerRight : undefined"),
    ).toBe(true);
  });
});
