import { checkLedgerFileName } from "../utils";

// w21/275: New File refused any name with a dot, though the dialog says .bean
// is added when the extension is omitted.
describe("a dot inside a new file's name", () => {
  it("is part of the name, and .bean is added", () => {
    for (const [typed, made] of [
      ["2024.q1", "2024.q1.bean"],
      ["v1.2 notes", "v1.2 notes.bean"],
      ["J.Smith accounts", "J.Smith accounts.bean"],
      ["Jan. expenses", "Jan. expenses.bean"],
      ["sub/2024.q1", "sub/2024.q1.bean"],
      ["notes.", "notes.bean"],
    ]) {
      expect(checkLedgerFileName(typed)).toEqual({ ok: true, filename: made });
    }
  });

  it("still refuses another explicit extension", () => {
    for (const typed of ["notes.txt", "data.csv", "sub/readme.md"]) {
      expect(checkLedgerFileName(typed)).toEqual({
        ok: false,
        issue: "extension",
      });
    }
  });

  it("keeps .bean and .beancount names as typed", () => {
    expect(checkLedgerFileName("2024.q1.bean")).toEqual({
      ok: true,
      filename: "2024.q1.bean",
    });
    expect(checkLedgerFileName("a.BEANCOUNT")).toEqual({
      ok: true,
      filename: "a.BEANCOUNT",
    });
  });
});
