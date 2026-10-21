import fs from "fs";
import path from "path";
import { scaleLineHeights } from "../dynamic-type";

// w21/111: Dynamic Type grew the drawer's text but not its fixed line heights,
// so at AX2 each name showed only its top half.
describe("scaleLineHeights", () => {
  const styles = {
    name: { fontSize: 16, lineHeight: 24 },
    plain: { fontSize: 14 },
  };

  it("leaves the default and smaller sizes exactly as they were", () => {
    expect(scaleLineHeights(styles, 1)).toBe(styles);
    expect(scaleLineHeights(styles, 0.85)).toBe(styles);
    expect(scaleLineHeights(styles, undefined)).toBe(styles);
  });

  it("grows each line height with the text at AX2", () => {
    const scaled = scaleLineHeights(styles, 1.8);
    expect(scaled.name).toEqual({ fontSize: 16, lineHeight: 44 });
    expect(scaled.plain).toBe(styles.plain);
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
    expect(
      source.includes("useThemeStyle(getStyles);\n  const { fontScale }"),
    ).toBe(true);
    expect(source.split("const styles = useDrawerStyles();").length - 1).toBe(
      3,
    );
  });
});
