import { newLedgerErrorDetail } from "../ledger-refusal";
import { runLedgerWrite, type LedgerWriteDeps } from "../ledger-write";

// A structured write that would add bean-check errors is refused as
// VALIDATION_FAILED on `entries`, its reason naming each new error (w0/m2).
// The app shows what it would break instead of a generic failure.
const refusal = (
  reason: string,
  field = "entries",
  code = "VALIDATION_FAILED",
) =>
  Object.assign(new Error(`Validation failed for ${field}: ${reason}`), {
    graphQLErrors: [{ message: reason, extensions: { code, field, reason } }],
  });

describe("newLedgerErrorDetail", () => {
  it("names the error a refused write would add", () => {
    expect(
      newLedgerErrorDetail(
        refusal(
          "adding these entries would introduce 1 new bean-check error: Duplicate open directive for Assets:Cash (main.bean:74)",
        ),
      ),
    ).toBe("Duplicate open directive for Assets:Cash (main.bean:74)");
  });

  it("keeps several named errors together", () => {
    expect(
      newLedgerErrorDetail(
        refusal(
          "adding these entries would introduce 2 new bean-check errors: A (main.bean:1); B (main.bean:2)",
        ),
      ),
    ).toBe("A (main.bean:1); B (main.bean:2)");
  });

  it("ignores other refusals, fields and failures", () => {
    expect(newLedgerErrorDetail(refusal("Must be lowercase", "username"))).toBe(
      null,
    );
    expect(
      newLedgerErrorDetail(
        refusal(
          "introduce 1 new bean-check error: X",
          "entries",
          "BAD_USER_INPUT",
        ),
      ),
    ).toBe(null);
    expect(newLedgerErrorDetail(new Error("Network request failed"))).toBe(
      null,
    );
    expect(newLedgerErrorDetail(undefined)).toBe(null);
  });
});

describe("runLedgerWrite with a refusal it can describe", () => {
  const deps = (toasts: string[]): LedgerWriteDeps => ({
    showToast: (message) => {
      toasts.push(message);
      return () => undefined;
    },
    haptics: { success: () => undefined, error: () => undefined },
    goBack: () => undefined,
    describeRefusal: (error) => {
      const detail = newLedgerErrorDetail(error);
      return detail ? `Would break: ${detail}` : null;
    },
  });

  it("toasts what the write would break instead of the generic failure", async () => {
    const toasts: string[] = [];
    const outcome = await runLedgerWrite(deps(toasts), {
      perform: async () => {
        throw refusal(
          "adding these entries would introduce 1 new bean-check error: Duplicate open directive for Assets:Cash (main.bean:74)",
        );
      },
      successMessage: "Saved",
      failureMessage: "Could not save",
    });
    expect(outcome.ok).toBe(false);
    expect(toasts).toEqual([
      "Would break: Duplicate open directive for Assets:Cash (main.bean:74)",
    ]);
  });

  it("keeps the generic failure for anything else", async () => {
    const toasts: string[] = [];
    await runLedgerWrite(deps(toasts), {
      perform: async () => {
        throw new Error("Network request failed");
      },
      successMessage: "Saved",
      failureMessage: "Could not save",
    });
    expect(toasts).toEqual(["Could not save"]);
  });

  it("lets a screen's own failure copy win", async () => {
    const toasts: string[] = [];
    await runLedgerWrite(deps(toasts), {
      perform: async () => {
        throw refusal(
          "adding these entries would introduce 1 new bean-check error: X",
        );
      },
      successMessage: "Saved",
      failureMessage: "Could not save",
      failureMessageFor: () => "Delete failed: entry changed",
    });
    expect(toasts).toEqual(["Delete failed: entry changed"]);
  });
});
