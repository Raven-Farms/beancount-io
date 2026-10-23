import fs from "fs";
import path from "path";
import { relaxLineHeights } from "../dynamic-type";

// w21/111 pinned a point line height that clipped each drawer name to its top
// half at AX2; the fix that grew line heights with the text size double-scaled
// what React Native already scales, so lines were about twice as tall and a
// wrapped name split far apart (w21/247).
describe("relaxLineHeights", () => {
  const styles = {
    name: { fontSize: 16, lineHeight: 24, fontWeight: "500" },
    plain: { fontSize: 14 },
  };

  it("leaves the default and smaller sizes exactly as they were", () => {
    expect(relaxLineHeights(styles, 1)).toBe(styles);
    expect(relaxLineHeights(styles, 0.85)).toBe(styles);
    expect(relaxLineHeights(styles, undefined)).toBe(styles);
    expect(relaxLineHeights(styles, Number.NaN)).toBe(styles);
  });

  it("drops the fixed line height once text is enlarged, keeping the rest", () => {
    const relaxed = relaxLineHeights(styles, 2.15);
    expect(relaxed.name).toEqual({ fontSize: 16, fontWeight: "500" });
    expect("lineHeight" in relaxed.name).toBe(false);
    expect(relaxed.plain).toBe(styles.plain);
  });

  it("never multiplies a line height by the text size", () => {
    // The platform scales a point line height itself.
    const themeDir = path.join(__dirname, "..");
    for (const file of fs.readdirSync(themeDir)) {
      if (!/\.tsx?$/.test(file)) continue;
      const source = fs.readFileSync(path.join(themeDir, file), "utf8");
      expect(
        /lineHeight\s*\*\s*fontScale|fontScale\s*\*\s*lineHeight/.test(source),
      ).toBe(false);
    }
  });

  it("is what every drawer component styles with", () => {
    const source = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "..",
        "..",
        "components",
        "ledger-drawer",
        "ledger-drawer.tsx",
      ),
      "utf8",
    );
    expect(source.includes("relaxLineHeights(styles, fontScale)")).toBe(true);
    expect(source.includes("scaleLineHeights")).toBe(false);
    expect(source.split("const styles = useDrawerStyles();").length - 1).toBe(
      3,
    );
  });
});
