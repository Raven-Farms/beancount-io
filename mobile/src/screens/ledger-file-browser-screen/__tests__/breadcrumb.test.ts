import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";
import { parentDirectory } from "../utils";

// w21/277: a deep breadcrumb cut off the current folder ("…/Checking/2026"
// hid 2026), and the up button did not name where it goes.
describe("the Files breadcrumb", () => {
  const source = fs
    .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
    .replace(/\s+/g, "");

  it("keeps the current folder visible by cutting the head", () => {
    expect(
      source.includes(
        '<Textstyle={styles.breadcrumbText}numberOfLines={1}ellipsizeMode="head">',
      ),
    ).toBe(true);
  });

  it("names the folder the up button goes to", () => {
    expect(
      source.includes('t("ledgerNavigateUpTo",{folder:parentFolder})'),
    ).toBe(true);
    expect(en.ledgerNavigateUpTo.replace("{{folder}}", "Checking")).toBe(
      "Go up to Checking",
    );
    const parent = (p: string) => parentDirectory(p).split("/").pop();
    expect(parent("documents/Assets/US/BofA/Checking/2026")).toBe("Checking");
    // A first-level folder goes up to the root, which has no name.
    expect(parent("documents")).toBe("");
  });
});
