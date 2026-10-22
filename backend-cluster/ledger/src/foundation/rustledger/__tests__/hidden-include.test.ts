import type { FileMap } from "@rustledger/wasm";
import { collectSourceFiles } from "../file-map-loader";
import { parseableFiles } from "../undecodable-sources";

/**
 * w21/657. The FileMap holds every `.bean` file, and rustledger's glob matched
 * `y/.hidden.bean` for `include "y/*.bean"`, so a hidden draft counted in
 * hosted balances that Beancount (Python's glob skips hidden names) and `bea`
 * leave out.
 */
const tx = (narration: string) =>
  `2020-01-02 * "${narration}"\n  Assets:Cash 1 USD\n  Equity:Open\n`;
const ledger = (main: string): FileMap => ({
  "main.bean": main,
  "y/a.bean": tx("a"),
  "y/.hidden.bean": tx("hidden"),
  ".archive/old.bean": tx("old"),
});

describe("a hidden file in an included folder", () => {
  it("is not reached, or parsed, through a glob", () => {
    const files = ledger('include "y/*.bean"\ninclude "**/*.bean"\n');
    expect(collectSourceFiles(files, "main.bean")).toEqual([
      "main.bean",
      "y/a.bean",
    ]);
    expect(Object.keys(parseableFiles(files, "main.bean")).sort()).toEqual([
      "main.bean",
      "y/a.bean",
    ]);
  });

  it("is parsed when an include names it or a pattern starts with a dot", () => {
    const named = ledger('include "y/.hidden.bean"\n');
    expect(Object.keys(parseableFiles(named, "main.bean"))).toContain(
      "y/.hidden.bean",
    );
    const dotted = ledger('include "y/.*.bean"\ninclude ".archive/*.bean"\n');
    expect(Object.keys(parseableFiles(dotted, "main.bean")).sort()).toEqual([
      ".archive/old.bean",
      "main.bean",
      "y/.hidden.bean",
      "y/a.bean",
    ]);
  });

  it("leaves a map with no hidden or undecodable file as it is", () => {
    const files: FileMap = {
      "main.bean": 'include "y/*.bean"\n',
      "y/a.bean": "",
    };
    expect(parseableFiles(files, "main.bean")).toBe(files);
  });
});
