import fs from "fs";
import path from "path";

// w21/558: a menu item's icon is a glyph in a Text node, so VoiceOver read
// "Enter new transaction, <glyph>, button". The label guardrail missed it
// because the icon arrives as a prop; this one names the menu.
const source = fs
  .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
  .replace(/\s+/g, "");

describe("a menu item's accessibility", () => {
  it("is named by its label, not by its children", () => {
    const item = source.slice(source.indexOf("items.map((item,i)=>"));
    expect(item.includes("accessibilityLabel={item.label}")).toBe(true);
  });

  it("hides the icon from assistive technology", () => {
    expect(
      source.includes(
        '<ViewaccessibilityElementsHiddenimportantForAccessibility="no-hide-descendants">{item.icon}</View>',
      ),
    ).toBe(true);
  });
});
