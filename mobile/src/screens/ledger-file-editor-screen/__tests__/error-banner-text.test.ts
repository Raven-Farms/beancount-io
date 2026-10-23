import fs from "fs";
import path from "path";

// w21/312: the editor's error banner cut a message at two lines, so the skipped
// plugin's "effects were not applied" and a URL include's whole guidance were
// only in Notifications. The banner's list is capped at 140 pt and scrolls.
describe("the file editor's error banner", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "index.tsx"),
    "utf8",
  );
  const compact = source.replace(/\s+/g, "");
  const banner = compact.slice(
    compact.indexOf('testID="ledger-editor-error-list"'),
    compact.indexOf(
      "</ScrollView>",
      compact.indexOf("ledger-editor-error-list"),
    ),
  );

  it("shows a message whole instead of cutting it at two lines", () => {
    expect(banner.includes("styles.errorText")).toBe(true);
    expect(banner.includes("numberOfLines")).toBe(false);
  });

  it("scrolls its list whatever the row count, since a long row can overflow", () => {
    expect(banner.includes("scrollEnabled")).toBe(true);
    expect(banner.includes("scrollEnabled={errors.length")).toBe(false);
    expect(/errorList:\{maxHeight:140,/.test(compact)).toBe(true);
  });
});
