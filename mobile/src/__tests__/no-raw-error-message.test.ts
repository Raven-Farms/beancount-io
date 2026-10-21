import fs from "fs";
import path from "path";

/**
 * w21/117: failed writes showed "Network request failed", "OAuth refresh
 * failed" or "Received status code 502" raw, in English, as if the ledger had
 * refused them. Writes go through `ledgerWriteFailureMessage`; this guard
 * fails on a reintroduced `error.message` fallback in a screen or component.
 * The mobile counterpart of the dashboard's no-raw-error-message check.
 */
const roots = ["screens", "components"].map((dir) =>
  path.join(__dirname, "..", dir),
);

// Modules that read an error's text to classify it, never to show it.
const CLASSIFIERS = [
  path.join("screens", "agent-screen", "agent-errors.ts"),
  path.join("screens", "receipt-capture-screen", "use-receipt-workflow.ts"),
  path.join("screens", "create-ledger-screen", "ledger-name.ts"),
];

const RAW_FALLBACK = [
  /instanceof Error\s*\?\s*\w+\.message/,
  /\?\s*\w*[Ee]rror\.message\b/,
];

function sourceFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      return entry.name === "__tests__" ? [] : sourceFiles(full);
    }
    return /\.tsx?$/.test(entry.name) ? [full] : [];
  });
}

describe("failed writes in the UI", () => {
  it("never fall back to an error's raw message", () => {
    const srcDir = path.join(__dirname, "..");
    const offenders = roots
      .flatMap(sourceFiles)
      .filter((file) => !CLASSIFIERS.includes(path.relative(srcDir, file)))
      .flatMap((file) =>
        fs
          .readFileSync(file, "utf8")
          .split("\n")
          .map((line, i) => ({
            line,
            at: `${path.relative(srcDir, file)}:${i + 1}`,
          }))
          // Conflict detection reads the server's text; it shows nothing.
          .filter(({ line }) => !line.includes("isConflictError("))
          .filter(({ line }) =>
            RAW_FALLBACK.some((pattern) => pattern.test(line)),
          )
          .map(({ at }) => at),
      );
    expect(offenders.join(", ")).toBe("");
  });

  it("catches the pattern it guards against", () => {
    const sample =
      "const message = deleteError instanceof Error ? deleteError.message : t('x');";
    expect(RAW_FALLBACK.some((pattern) => pattern.test(sample))).toBe(true);
  });
});
