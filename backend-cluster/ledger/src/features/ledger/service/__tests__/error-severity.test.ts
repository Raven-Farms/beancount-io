import type { BeancountError } from "@rustledger/wasm";
import { toBeancountErrorsPublic } from "../ledger-data-mappers";

// w21/188: the engine marks a one-posting entry and closing an account with a
// balance as warnings while bean-check passes; the DTO dropped that.
const raw = (severity: BeancountError["severity"], message: string) =>
  ({
    message,
    code: "E3004",
    phase: "validate",
    hint: null,
    file: "main.bean",
    line: 90,
    column: 1,
    end_line: null,
    end_column: null,
    severity,
  }) as BeancountError;

describe("toBeancountErrorsPublic severity", () => {
  it("keeps a warning a warning and everything else an error", () => {
    expect(
      toBeancountErrorsPublic([
        raw("warning", "Transaction has only one posting"),
        raw("error", "Transaction does not balance"),
      ]).map((error) => error.severity),
    ).toEqual(["warning", "error"]);
  });
});
