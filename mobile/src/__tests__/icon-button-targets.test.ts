import fs from "fs";
import path from "path";
import { iconActionSize } from "../common/theme/spacing";

// w21/485: the Files "Up" control and the budget history Delete were about
// 26-28 pt around their icons. Their styles read layout constants getStyles
// cannot evaluate outside the app, so the sizing is checked on the source.
const style = (file: string, key: string) => {
  const source = fs
    .readFileSync(path.join(__dirname, "..", file), "utf8")
    .replace(/\s+/g, "");
  const start = source.indexOf(`${key}:{`);
  expect(start > -1).toBe(true);
  return source.slice(start, source.indexOf("},", start));
};

describe("small icon buttons are 44 pt targets", () => {
  it("uses the shared icon action size", () => {
    expect(iconActionSize).toBe(44);
  });

  for (const [name, file, key] of [
    [
      "the Files Up breadcrumb",
      "screens/ledger-file-browser-screen/index.tsx",
      "breadcrumbBack",
    ],
    [
      "the budget history Delete",
      "screens/budget-screen/components/budget-history-rows.tsx",
      "deleteButton",
    ],
  ]) {
    it(`${name} is at least 44 x 44`, () => {
      const block = style(file!, key!);
      expect(block.includes("minWidth:iconActionSize")).toBe(true);
      expect(block.includes("minHeight:iconActionSize")).toBe(true);
      // Centred, so the icon does not slide into a corner.
      expect(block.includes('alignItems:"center"')).toBe(true);
      expect(block.includes('justifyContent:"center"')).toBe(true);
    });
  }
});
