import fs from "fs";
import path from "path";

/**
 * w21/357: `onRequestClose` does not handle VoiceOver's two-finger scrub, and
 * the dialogs' titles were plain text. Source checks; the components need the
 * native runtime.
 */
const read = (relative: string) =>
  fs
    .readFileSync(path.join(__dirname, "../../..", relative), "utf8")
    .replace(/\s+/g, "");

describe("the Picker and the text-input modal for VoiceOver", () => {
  it("the Picker dismisses on escape as Cancel does and names its title a heading", () => {
    const src = read("components/picker/index.tsx");
    expect(src.includes("onAccessibilityEscape={handleCancel}")).toBe(true);
    expect(
      src.includes(
        'style={styles.title}numberOfLines={1}accessibilityRole="header"',
      ),
    ).toBe(true);
  });

  it("the text-input modal dismisses on escape and names its title a heading", () => {
    const src = read("components/text-input-modal/index.tsx");
    expect(src.includes("onAccessibilityEscape={onCancel}")).toBe(true);
    expect(
      src.includes('<Textstyle={styles.title}accessibilityRole="header">'),
    ).toBe(true);
  });
});
