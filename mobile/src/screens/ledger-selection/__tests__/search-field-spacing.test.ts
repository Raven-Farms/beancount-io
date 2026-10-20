import fs from "fs";
import path from "path";

/**
 * Browse ledgers hand-rolls its search field. Its magnifier touched the
 * placeholder until the row got the same `gap: space.sm` as the shared
 * SearchBar and Merchants (w21/002); this keeps the copies from drifting.
 */
const styleBlock = (file: string, name: string) => {
  const source = fs.readFileSync(file, "utf8");
  const start = source.indexOf(`    ${name}: {`);
  return start < 0 ? "" : source.slice(start, source.indexOf("},", start));
};

describe("Browse ledgers search field", () => {
  it("spaces the magnifier from the text like the shared search bar", () => {
    const screen = path.join(__dirname, "..", "index.tsx");
    const shared = path.join(
      __dirname,
      "..",
      "..",
      "..",
      "components",
      "search-bar",
      "index.tsx",
    );
    expect(styleBlock(shared, "field").includes("gap: space.sm")).toBe(true);
    expect(styleBlock(screen, "search").includes("gap: space.sm")).toBe(true);
  });
});
