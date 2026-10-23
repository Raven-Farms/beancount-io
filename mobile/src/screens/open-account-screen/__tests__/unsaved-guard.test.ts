import fs from "fs";
import path from "path";

// w21/631: Open Account and Add Budget dropped a typed name or amount on Back
// without asking, where New Transaction, Edit and the file editor ask first. The
// screens need the native runtime, so the wiring is checked on source; the
// guard itself is covered by use-unsaved-changes-guard.test.
const read = (...parts: string[]) =>
  fs
    .readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8")
    .replace(/\s+/g, "");

describe("Back from a dirty short form", () => {
  it("asks before Open Account drops a typed name", () => {
    const screen = read("open-account-screen", "open-account-screen.tsx");
    expect(
      screen.includes(
        "useUnsavedChangesGuard(!saved&&subPath!==seed.subPath,savedOutRef);",
      ),
    ).toBe(true);
    expect(screen.includes("savedOutRef.current=true;setSaved(true);")).toBe(
      true,
    );
  });

  it("asks before Add Budget drops a typed amount", () => {
    const screen = read("add-budget-screen", "add-budget-screen.tsx");
    expect(
      screen.includes(
        "useUnsavedChangesGuard(!saved&&amount.trim().length>0,savedOutRef);",
      ),
    ).toBe(true);
    expect(
      screen.includes(
        "haptics.success();savedOutRef.current=true;setSaved(true);",
      ),
    ).toBe(true);
  });
});
