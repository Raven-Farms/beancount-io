import { newLedgerErrors } from "../new-ledger-errors";

const at = (message: string, filename: string, lineno: number) => ({
  message,
  source: { filename, lineno },
});

describe("newLedgerErrors", () => {
  it("returns only the errors the projection adds", () => {
    const before = [at("Balance failed for Assets:Cash", "main.bean", 4)];
    const after = [
      at("Balance failed for Assets:Cash", "main.bean", 4),
      at("Duplicate open directive for Assets:Cash", "main.bean", 12),
    ];
    expect(newLedgerErrors(before, after)).toEqual([
      at("Duplicate open directive for Assets:Cash", "main.bean", 12),
    ]);
  });

  it("treats the same message at another position as new", () => {
    const before = [
      at("Duplicate open directive for Assets:Cash", "main.bean", 3),
    ];
    const after = [
      at("Duplicate open directive for Assets:Cash", "main.bean", 3),
      at("Duplicate open directive for Assets:Cash", "main.bean", 9),
    ];
    expect(newLedgerErrors(before, after)).toEqual([after[1]]);
  });

  it("matches errors without a source by message", () => {
    expect(
      newLedgerErrors(
        [{ message: "Plugin failed" }],
        [{ message: "Plugin failed" }],
      ),
    ).toEqual([]);
    expect(newLedgerErrors([], [{ message: "Plugin failed" }])).toEqual([
      { message: "Plugin failed" },
    ]);
  });

  it("finds nothing new for a clean write", () => {
    expect(newLedgerErrors([], [])).toEqual([]);
  });
});
