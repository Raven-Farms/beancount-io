import fs from "fs";
import path from "path";
import { selectEntryErrors } from "../select-entry-errors";

// A transaction the ledger reports as broken opened with no sign of it
// (w21/030). The errors that point into its own lines show on its detail.
const SOURCE = {
  filename: "main.bean",
  lineno: 89,
  slice: [
    '2026-10-20 * "qa-20261020-err"',
    "  Assets:Cash  -1.00 USD",
    "  Expenses:Transport  2.00 USD",
    "",
  ].join("\n"),
};
const at = (lineno: number | null, message = "e", filename = "main.bean") => ({
  message,
  filename,
  lineno,
});

describe("selectEntryErrors", () => {
  it("keeps errors on the entry's first line and on its postings", () => {
    const residual = at(89, "Transaction does not balance: residual 1.00 USD");
    const posting = at(
      90,
      "Invalid reference to unknown account 'Assets:Nope'",
    );
    expect(selectEntryErrors([residual, posting], SOURCE)).toEqual([
      residual,
      posting,
    ]);
  });

  it("leaves out the line before, the next entry, and other files", () => {
    expect(
      selectEntryErrors(
        [at(88), at(92), at(89, "e", "other.bean"), at(null)],
        SOURCE,
      ),
    ).toEqual([]);
  });

  it("matches an error that names the file by a longer path", () => {
    expect(
      selectEntryErrors([at(91, "e", "/repo/main.bean")], SOURCE).length,
    ).toBe(1);
  });

  // w21/089: a same-named file elsewhere is not this entry's file.
  it("leaves out errors from a same-named file in another folder", () => {
    const nested = { ...SOURCE, filename: "2026/transactions.bean", lineno: 3 };
    expect(
      selectEntryErrors([at(4, "e", "2025/transactions.bean")], nested),
    ).toEqual([]);
    expect(
      selectEntryErrors([at(90, "e", "main.bean")], {
        ...SOURCE,
        filename: "qa/main.bean",
      }),
    ).toEqual([]);
    expect(
      selectEntryErrors([at(4, "e", "2026/transactions.bean")], nested).length,
    ).toBe(1);
  });

  it("shows nothing without the entry's source location", () => {
    expect(selectEntryErrors([at(89)], null)).toEqual([]);
  });

  it("is rendered above Money flow with a way into the file editor", () => {
    const screen = fs.readFileSync(
      path.join(__dirname, "..", "..", "transaction-detail-screen.tsx"),
      "utf8",
    );
    expect(screen.includes('testID="transaction-errors"')).toBe(true);
    expect(
      screen.includes("onPress={() => openErrorInEditor(entryErrors[0]!)}"),
    ).toBe(true);
    expect(
      screen.indexOf('testID="transaction-errors"') <
        screen.indexOf('{t("moneyFlow")}'),
    ).toBe(true);
  });
});
