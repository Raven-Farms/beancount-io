import { commitFileRows } from "../diff-utils";

/**
 * w21/132: FILES showed a rename as two "+0 −0" files, and an empty file's
 * creation looked the same as its deletion.
 */
const rename = [
  "diff --git a/qa-a.bean b/qa-c.bean",
  "similarity index 100%",
  "rename from qa-a.bean",
  "rename to qa-c.bean",
  "diff --git a/books.bean b/books.bean",
  "--- a/books.bean",
  "+++ b/books.bean",
  "@@ -1 +1,2 @@",
  " keep",
  "+rename from a line that reads like a header",
].join("\n");
const files = [
  { filename: "books.bean", additions: 1, deletions: 0 },
  { filename: "qa-a.bean", additions: 0, deletions: 0 },
  { filename: "qa-c.bean", additions: 0, deletions: 0 },
];

describe("commitFileRows", () => {
  it("collapses a rename into one row that names the old path", () => {
    expect(commitFileRows(files, rename)).toEqual([
      { ...files[0], status: "modified", previousFilename: null },
      { ...files[2], status: "renamed", previousFilename: "qa-a.bean" },
    ]);
  });

  it("tells an empty file's creation from its deletion", () => {
    const row = [{ filename: "qa/n.bean", additions: 0, deletions: 0 }];
    const header = "diff --git a/qa/n.bean b/qa/n.bean\n";
    expect(
      commitFileRows(row, `${header}new file mode 100644\n`)[0].status,
    ).toBe("added");
    expect(
      commitFileRows(row, `${header}deleted file mode 100644\n`)[0].status,
    ).toBe("removed");
  });

  it("keeps every row as an edit when the diff is missing", () => {
    expect(commitFileRows(files, null).map((row) => row.status)).toEqual([
      "modified",
      "modified",
      "modified",
    ]);
  });
});
