import fs from "fs";
import path from "path";

// w21/604: a posting's metadata was cut to two lines and could not be selected,
// so a 120-character receipt link ended in "…". Source check (the row needs the
// native runtime).
const row = fs
  .readFileSync(path.join(__dirname, "..", "posting-row.tsx"), "utf8")
  .replace(/\s+/g, "");

describe("a posting's metadata lines", () => {
  it("are shown whole and can be selected", () => {
    const lines = row.slice(row.indexOf("{posting.meta?.map((line)=>("));
    const text = lines.slice(0, lines.indexOf("))}"));
    expect(
      text.includes("<Textstyle={styles.metaLine}key={line}selectable>"),
    ).toBe(true);
    expect(text.includes("numberOfLines")).toBe(false);
  });

  it("are still part of the row's spoken label", () => {
    expect(row.includes("posting.meta.join(")).toBe(true);
  });
});
