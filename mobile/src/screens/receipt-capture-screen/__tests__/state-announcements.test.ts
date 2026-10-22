import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

// w21/284: Upload makes the focused button disappear; the uploading, error and
// reveal states that replace it were silent to VoiceOver, and the form opened
// 1.2 s after the reveal. These views use native hooks this runner cannot
// execute, so the wiring is checked on their source.
describe("the receipt screen's states are announced", () => {
  const read = (name: string) =>
    fs
      .readFileSync(path.join(__dirname, "..", name), "utf8")
      .replace(/\s+/g, "");
  const preview = read("preview-view.tsx");

  it("says the uploading, parsing, error and reveal states aloud", () => {
    expect(
      preview.includes(
        "AccessibilityInfo.announceForAccessibility(announcement)",
      ),
    ).toBe(true);
    expect(preview.includes('status==="uploading"?t("receiptUploading")')).toBe(
      true,
    );
    expect(preview.includes('status==="parsing"?t("receiptParsing")')).toBe(
      true,
    );
    expect(preview.includes('status==="error"?(errorMessage??null)')).toBe(
      true,
    );
    expect(preview.includes('t("receiptRevealSpoken"')).toBe(true);
    expect(preview.includes('accessibilityRole="alert"')).toBe(true);
    expect(read("reveal-view.tsx").includes('accessibilityRole="header"')).toBe(
      true,
    );
  });

  it("gives a screen reader time to finish before the form opens", () => {
    const screen = read("receipt-capture-screen.tsx");
    expect(
      screen.includes(
        "screenReader.current?REVEAL_DWELL_SCREEN_READER_MS:REVEAL_DWELL_MS",
      ),
    ).toBe(true);
    expect(screen.includes("AccessibilityInfo.isScreenReaderEnabled()")).toBe(
      true,
    );
    expect(en.receiptRevealSpoken).toBe("Receipt read: {{summary}}");
  });

  it("gives every preview button a role", () => {
    const buttons = preview.split("<Pressable").length - 1;
    const roles = preview.split('accessibilityRole="button"').length - 1;
    expect(buttons).toBe(roles);
  });
});
