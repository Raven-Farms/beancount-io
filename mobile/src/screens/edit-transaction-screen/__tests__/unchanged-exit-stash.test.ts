import fs from "fs";
import path from "path";
import {
  selectStashedTransaction,
  selectedTransactionVar,
} from "../../transaction-detail-screen/open-transaction-detail";

/**
 * w21/388: an edit that kept the entry's hash (metadata, posting order) went
 * back to a detail screen that painted the copy stashed when the row was
 * opened, so the new metadata never showed.
 */
describe("an edit that keeps the entry's hash", () => {
  const entry = { entry_hash: "h1", meta: {} } as never;

  it("is shown from the stash while the stash holds it", () => {
    expect(
      selectStashedTransaction(
        { ledgerId: "alice/books", entry },
        { entryHash: "h1", ledgerId: "alice/books" },
      ),
    ).toBe(entry);
  });

  it("falls back to the refetched entry once the stash is cleared", () => {
    selectedTransactionVar({ ledgerId: "alice/books", entry });
    selectedTransactionVar(null);
    expect(
      selectStashedTransaction(selectedTransactionVar(), {
        entryHash: "h1",
        ledgerId: "alice/books",
      }),
    ).toBe(null);
  });

  it("clears the stash on the unchanged exit, whether or not the user is still here", () => {
    const src = fs
      .readFileSync(
        path.join(__dirname, "..", "edit-transaction-screen.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    const exit = src.indexOf(
      "constexit=resolveSaveExit(targetEntryHash,saved.entryHash);",
    );
    const here = src.indexOf("consthere=isHere();");
    const clear = src.indexOf(
      'if(exit.kind==="unchanged")selectedTransactionVar(null);',
    );
    expect(exit > -1 && clear > exit).toBe(true);
    expect(clear < src.indexOf('}elseif(here&&exit.kind==="unchanged"){')).toBe(
      true,
    );
    expect(here > -1).toBe(true);
  });
});
