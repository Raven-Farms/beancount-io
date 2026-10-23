import fs from "fs";
import path from "path";

/**
 * w21/356: iOS drops the `tab` role and never speaks "collapsed". The module
 * imports react-native, so it is loaded with a stub for it.
 */
function load(os: string) {
  const ts = require("typescript");
  const vm = require("vm");
  const source = ts.transpileModule(
    fs.readFileSync(path.join(__dirname, "../accessibility.ts"), "utf8"),
    { compilerOptions: { module: ts.ModuleKind.CommonJS } },
  ).outputText;
  const exports: Record<string, any> = {};
  vm.runInNewContext(source, {
    exports,
    require: (id: string) => {
      if (id !== "react-native") throw new Error(`Unexpected dependency ${id}`);
      return { Platform: { OS: os } };
    },
  });
  return exports;
}

const t = (key: string) => key;

describe("disclosureAccessibility", () => {
  const { disclosureAccessibility } = load("ios");

  it("says what a double tap does when collapsed and when expanded", () => {
    expect(JSON.stringify(disclosureAccessibility(false, t))).toBe(
      JSON.stringify({
        accessibilityState: { expanded: false },
        accessibilityHint: "a11yTapToExpand",
      }),
    );
    expect(JSON.stringify(disclosureAccessibility(true, t))).toBe(
      JSON.stringify({
        accessibilityState: { expanded: true },
        accessibilityHint: "a11yTapToCollapse",
      }),
    );
  });
});

describe("tabRole", () => {
  it("is a button on iOS, where the tab role carries no trait, and a tab elsewhere", () => {
    expect(load("ios").tabRole).toBe("button");
    expect(load("android").tabRole).toBe("tab");
  });
});

describe("the expandable rows and tab bars", () => {
  const read = (relative: string) =>
    fs.readFileSync(path.join(__dirname, "../..", relative), "utf8");

  it("every row that reports an expanded state also hints its action", () => {
    for (const file of [
      "screens/reports-screen/components/category-breakdown.tsx",
      "screens/budget-screen/components/budget-history-rows.tsx",
      "screens/ledger-file-editor-screen/index.tsx",
      "screens/transactions-screen/entry-context/index.tsx",
    ]) {
      const src = read(file);
      expect(src.includes("{...disclosureAccessibility(")).toBe(true);
      expect(/accessibilityState=\{\{\s*expanded/.test(src)).toBe(false);
    }
  });

  it("the tab bars use the platform tab role", () => {
    for (const file of [
      "components/segmented-pages/index.tsx",
      "screens/ledger-selection/index.tsx",
    ]) {
      const src = read(file);
      expect(src.includes("accessibilityRole={tabRole}")).toBe(true);
      expect(src.includes('accessibilityRole="tab"')).toBe(false);
    }
  });
});
