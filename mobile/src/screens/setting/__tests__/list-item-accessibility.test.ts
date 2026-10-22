import fs from "fs";
import path from "path";
import { listItemLabel } from "../list-item-label";

// w21/287: VoiceOver never read a Settings row's description (including
// "Deleting account…"), and read the Version row as "dimmed".
describe("listItemLabel", () => {
  it("speaks the description with the title", () => {
    expect(
      listItemLabel({
        title: "Delete Account",
        description: "Permanently remove your account and data",
      }),
    ).toBe("Delete Account, Permanently remove your account and data");
    expect(
      listItemLabel({
        title: "Delete Account",
        description: "Deleting account…",
      }),
    ).toBe("Delete Account, Deleting account…");
  });

  it("keeps the value, then the description", () => {
    expect(listItemLabel({ title: "Version", content: "1.2.3" })).toBe(
      "Version, 1.2.3",
    );
    expect(
      listItemLabel({
        title: "Language",
        content: "Deutsch",
        description: "x",
      }),
    ).toBe("Language, Deutsch, x");
  });

  it("leaves a non-text title to its children", () => {
    expect(listItemLabel({ title: {}, content: "x" })).toBe(undefined);
    expect(listItemLabel({ title: "Plain" })).toBe("Plain");
  });
});

describe("the Settings row", () => {
  const read = (name: string) =>
    fs
      .readFileSync(path.join(__dirname, "..", name), "utf8")
      .replace(/\s+/g, "");

  it("is a plain readable view when it has no action, not a disabled button", () => {
    const row = read("list-item.tsx");
    expect(row.includes("disabled={!onPress}")).toBe(false);
    expect(row.includes("onPress?(<TouchableOpacity")).toBe(true);
    expect(
      row.includes(":(<Viewstyle={styles.container}testID={testID}accessible"),
    ).toBe(true);
    expect(row.includes("accessibilityState={{busy}}")).toBe(true);
  });

  it("announces Delete Account as busy while it runs", () => {
    expect(
      read("main-content.tsx").includes("busy={deleteAccountLoading}"),
    ).toBe(true);
  });
});
