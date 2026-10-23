import fs from "fs";
import path from "path";

// w21/639: the denied screen's camera and the reveal's sparkles were VoiceOver
// stops of their own (a vector icon renders as Text, so the glyph was read).
// Source check (the screens need the native runtime), as w21/605's.
const compact = (file: string) =>
  fs.readFileSync(path.join(__dirname, "..", file), "utf8").replace(/\s+/g, "");

describe("Scan Receipt's decorative icons", () => {
  it("hide the denied screen's camera and the reveal's sparkles", () => {
    for (const [file, name] of [
      ["camera-view.tsx", "camera-outline"],
      ["reveal-view.tsx", "sparkles"],
    ]) {
      expect(
        compact(file).includes(
          `<Ioniconsname="${name}"accessibilityElementsHiddenimportantForAccessibility="no"`,
        ),
      ).toBe(true);
    }
  });
});
