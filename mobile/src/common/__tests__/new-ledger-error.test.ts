import { firstNewLedgerError } from "../new-ledger-error";

// A raw file save that leaves a new ledger error warns with it (w21/m1). The
// comparison must not blame the save for errors the ledger already had.
const balance = (lineno: number) => ({
  message: "Balance failed for Assets:Cash: expected 49.75 USD, got 73.25 USD",
  filename: "main.bean",
  lineno,
});
const duplicate = (lineno: number) => ({
  message: "Duplicate open directive for Assets:Cash",
  filename: "main.bean",
  lineno,
});

describe("firstNewLedgerError", () => {
  it("names the error a save added", () => {
    expect(firstNewLedgerError([], [balance(84)])).toEqual(balance(84));
  });

  it("ignores an existing error the save only moved", () => {
    expect(firstNewLedgerError([duplicate(90)], [duplicate(87)])).toBe(null);
  });

  it("counts a second copy of a known error as new", () => {
    expect(
      firstNewLedgerError([duplicate(3)], [duplicate(3), duplicate(9)]),
    ).toEqual(duplicate(9));
  });

  it("finds the new one among existing errors", () => {
    expect(
      firstNewLedgerError([duplicate(3)], [duplicate(3), balance(84)]),
    ).toEqual(balance(84));
  });

  it("reports nothing for a save that fixed an error", () => {
    expect(firstNewLedgerError([balance(84)], [])).toBe(null);
  });

  it("reports nothing without a snapshot from before the save", () => {
    expect(firstNewLedgerError(null, [balance(84)])).toBe(null);
    expect(firstNewLedgerError([], undefined)).toBe(null);
  });
});
