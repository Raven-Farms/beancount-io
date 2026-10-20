import fs from "fs";
import path from "path";
import { selectOutcomeFailure, selectSaveFailure } from "../save-failure";

describe("selectSaveFailure", () => {
  it("treats a stale checksum or a conflict as a conflict", () => {
    expect(selectSaveFailure("sha256sum mismatch: the entry changed")).toEqual({
      kind: "conflict",
    });
    expect(selectSaveFailure("HTTP 409 Conflict")).toEqual({
      kind: "conflict",
    });
  });

  it("keeps the server's own explanation for any other rejection", () => {
    expect(selectSaveFailure("Invalid beancount: unexpected token")).toEqual({
      kind: "rejected",
      message: "Invalid beancount: unexpected token",
    });
    expect(selectSaveFailure(undefined)).toEqual({
      kind: "rejected",
      message: null,
    });
  });
});

// The edit that re-dates FARMERS MARKET past its balance assertion is refused
// (w21/m1); Edit Transaction shows what it would break inline.
describe("selectOutcomeFailure", () => {
  const i18n = {
    t: (_key: "ledgerWouldBreak", { detail }: { detail: string }) =>
      `This would add an error to your ledger: ${detail}`,
  };
  const BALANCE_FAILED =
    "Balance failed for Assets:Cash: expected 49.75 USD, got 73.25 USD (main.bean:87)";

  it("names what a refused edit would break", () => {
    const error = Object.assign(
      new Error(
        `Validation failed for entry: this edit would introduce 1 new bean-check error: ${BALANCE_FAILED}`,
      ),
      {
        graphQLErrors: [
          {
            message: "Validation failed",
            extensions: {
              code: "VALIDATION_FAILED",
              field: "entry",
              newLedgerErrors: BALANCE_FAILED,
            },
          },
        ],
      },
    );
    expect(
      selectOutcomeFailure(
        { ok: false, message: "Couldn't save", error },
        i18n,
      ),
    ).toEqual({
      kind: "rejected",
      message: `This would add an error to your ledger: ${BALANCE_FAILED}`,
    });
  });

  it("still recognizes a stale checksum from the server's message", () => {
    expect(
      selectOutcomeFailure(
        {
          ok: false,
          message: "Couldn't save",
          error: new Error("sha256sum mismatch: the entry changed"),
        },
        i18n,
      ),
    ).toEqual({ kind: "conflict" });
  });

  it("falls back to the toast copy when the error says nothing", () => {
    expect(
      selectOutcomeFailure({ ok: false, message: "Couldn't save" }, i18n),
    ).toEqual({ kind: "rejected", message: "Couldn't save" });
  });
});

/**
 * Static guardrail over the screen, which the unit runner cannot render: a
 * conflict shows the translated message and offers a reload rather than the
 * raw server text.
 */
describe("Edit Transaction save-failure wiring", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "edit-transaction-screen.tsx"),
    "utf8",
  );

  it("reports a conflict with editConflict and offers Reload", () => {
    expect(source.includes("selectOutcomeFailure(outcome, i18n)")).toBe(true);
    expect(source.includes('setSaveError(t("editConflict"))')).toBe(true);
    expect(source.includes("onPress: () => void handleReload()")).toBe(true);
  });
});
