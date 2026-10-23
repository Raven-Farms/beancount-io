import { commentSkippedLines, parseableFiles } from "../parseable-files";

/**
 * w21/654. Beancount skips a whole line starting with `*`, `#`, `:`, `!`, `&`,
 * `?` or `%`; rustledger read a `"` on an org heading as an open string and
 * silently lost every entry after it. The live engine run is in
 * `scripts/verify-rustledger.ts`.
 */
describe("commentSkippedLines", () => {
  it("turns each line Beancount skips into a comment of the same length", () => {
    const source = [
      '* Notes: 12" pizza budget',
      "# It's 5\" wide",
      ': a "drawer',
      "! a",
      "& a",
      "? a",
      "% a",
      '2024-01-02 * "after"',
      "  Assets:Cash 1 USD",
      "  * Equity:Open",
      "",
    ].join("\n");
    const commented = commentSkippedLines(source);
    expect(commented.split("\n")).toEqual([
      '; Notes: 12" pizza budget',
      "; It's 5\" wide",
      '; a "drawer',
      "; a",
      "; a",
      "; a",
      "; a",
      '2024-01-02 * "after"',
      "  Assets:Cash 1 USD",
      // A flagged posting is indented, not a skipped line.
      "  * Equity:Open",
      "",
    ]);
    expect(commented).toHaveLength(source.length);
  });

  it("leaves a line inside a multi-line string, and a quote in a comment, alone", () => {
    const source = [
      '2024-01-01 note Assets:Cash "agenda:',
      "* first item",
      '# second item"',
      '; she said "hold',
      "* a real heading",
      "",
    ].join("\n");
    expect(commentSkippedLines(source).split("\n")).toEqual([
      '2024-01-01 note Assets:Cash "agenda:',
      "* first item",
      '# second item"',
      '; she said "hold',
      "; a real heading",
      "",
    ]);
  });

  it("returns a map with no such line unchanged", () => {
    const files = { "main.bean": '2024-01-01 open Assets:Cash\n; "quoted"\n' };
    expect(parseableFiles(files, "main.bean")).toBe(files);
    expect(
      parseableFiles({ "main.bean": "* Heading\n" }, "main.bean")["main.bean"],
    ).toBe("; Heading\n");
  });
});
