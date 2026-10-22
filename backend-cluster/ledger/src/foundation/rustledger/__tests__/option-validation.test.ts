import type { BeancountError } from "@rustledger/wasm";
import { reconcileOptionErrors } from "../option-validation";

// w21/308: Beancount's own default `account_previous_balances` and
// `account_rounding` raised red E7002 / E7007 errors that bean-check accepts.
const error = (
  message: string,
  severity: BeancountError["severity"] = "error",
): BeancountError => ({
  message,
  code: null,
  phase: null,
  hint: null,
  file: null,
  line: null,
  column: null,
  end_line: null,
  end_column: null,
  severity,
});

describe("reconcileOptionErrors", () => {
  it("drops E7002 for a valid leaf Beancount joins under Equity", () => {
    for (const leaf of ["Opening-Balances", "Rounding", "Earnings", "401k"]) {
      expect(
        reconcileOptionErrors([
          error(`[E7002] Invalid leaf account name: '${leaf}'`),
        ]),
      ).toEqual([]);
    }
  });

  it("keeps E7002 for a leaf that is not a valid component", () => {
    for (const leaf of [
      "rounding",
      "my rounding",
      "Under_score",
      "-Lead",
      "",
    ]) {
      const bad = error(`[E7002] Invalid leaf account name: '${leaf}'`);
      expect(reconcileOptionErrors([bad])).toEqual([bad]);
    }
  });

  it("downgrades E7007 to a warning and keeps its text", () => {
    const notice = error(
      "[E7007] Option 'account_rounding' is accepted for compatibility but has no effect: no rounding residual is produced.",
    );
    expect(reconcileOptionErrors([notice])).toEqual([
      { ...notice, severity: "warning" },
    ]);
  });

  it("leaves every other error alone, in order", () => {
    const others = [
      error("[E7006] Document root 'x' does not exist"),
      error("Balance failed", "error"),
      error("note", "warning"),
    ];
    expect(reconcileOptionErrors(others)).toEqual(others);
  });
});
