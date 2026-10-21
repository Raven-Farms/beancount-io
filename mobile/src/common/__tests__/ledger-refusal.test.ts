import {
  describeLedgerRefusal,
  ledgerWriteFailureMessage,
} from "../ledger-refusal";
import { runLedgerWrite, type LedgerWriteDeps } from "../ledger-write";

// A write that would add bean-check errors is refused as VALIDATION_FAILED,
// each new error named in `extensions.newLedgerErrors` (w0/m2). The app shows
// what it would break instead of a generic failure.
const refusal = (extensions: Record<string, unknown>) =>
  Object.assign(new Error("Validation failed for entries"), {
    graphQLErrors: [{ message: "Validation failed", extensions }],
  });
const wouldBreak = (named: string) =>
  refusal({
    code: "VALIDATION_FAILED",
    field: "entries",
    newLedgerErrors: named,
  });
const DUPLICATE_OPEN =
  "Duplicate open directive for Assets:Cash (main.bean:74)";
const i18n = {
  t: (key: string, params?: Record<string, string>) =>
    key === "ledgerWouldBreak" ? `Would break: ${params?.detail}` : key,
};

describe("describeLedgerRefusal", () => {
  it("names the error a refused write would add", () => {
    expect(describeLedgerRefusal(wouldBreak(DUPLICATE_OPEN), i18n)).toBe(
      `Would break: ${DUPLICATE_OPEN}`,
    );
  });

  it("keeps several named errors together, on either write path", () => {
    expect(
      describeLedgerRefusal(
        refusal({
          code: "VALIDATION_FAILED",
          field: "text",
          newLedgerErrors: "A (main.bean:1); B (main.bean:2)",
        }),
        i18n,
      ),
    ).toBe("Would break: A (main.bean:1); B (main.bean:2)");
  });

  it("ignores other refusals and failures", () => {
    expect(
      describeLedgerRefusal(
        refusal({ code: "VALIDATION_FAILED", field: "username" }),
        i18n,
      ),
    ).toBe(null);
    expect(
      describeLedgerRefusal(
        refusal({ code: "BAD_USER_INPUT", newLedgerErrors: DUPLICATE_OPEN }),
        i18n,
      ),
    ).toBe(null);
    expect(
      describeLedgerRefusal(
        refusal({ code: "VALIDATION_FAILED", newLedgerErrors: "  " }),
        i18n,
      ),
    ).toBe(null);
    expect(
      describeLedgerRefusal(new Error("Network request failed"), i18n),
    ).toBe(null);
    expect(describeLedgerRefusal(undefined, i18n)).toBe(null);
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
    describeRefusal: (error) => describeLedgerRefusal(error, i18n),
  });
  const failWith = (error: unknown) => async () => {
    throw error;
  };

  it("toasts what the write would break instead of the generic failure", async () => {
    const toasts: string[] = [];
    const outcome = await runLedgerWrite(deps(toasts), {
      perform: failWith(wouldBreak(DUPLICATE_OPEN)),
      successMessage: "Saved",
      failureMessage: "Could not save",
    });
    expect(outcome.ok).toBe(false);
    expect(toasts).toEqual([`Would break: ${DUPLICATE_OPEN}`]);
  });

  it("keeps the generic failure for anything else", async () => {
    const toasts: string[] = [];
    await runLedgerWrite(deps(toasts), {
      perform: failWith(new Error("Network request failed")),
      successMessage: "Saved",
      failureMessage: "Could not save",
    });
    expect(toasts).toEqual(["Could not save"]);
  });

  it("lets a screen's own failure copy win", async () => {
    const toasts: string[] = [];
    await runLedgerWrite(deps(toasts), {
      perform: failWith(wouldBreak(DUPLICATE_OPEN)),
      successMessage: "Saved",
      failureMessage: "Could not save",
      failureMessageFor: () => "Delete failed: entry changed",
    });
    expect(toasts).toEqual(["Delete failed: entry changed"]);
  });
});

// Open Account and Add Budget show the failure inline rather than through
// runLedgerWrite's toast.
describe("ledgerWriteFailureMessage", () => {
  it("describes a would-break refusal", () => {
    expect(ledgerWriteFailureMessage(wouldBreak(DUPLICATE_OPEN), i18n)).toBe(
      `Would break: ${DUPLICATE_OPEN}`,
    );
  });

  // w21/117: transport text reached the screen raw, in English, as if the
  // ledger had refused the write.
  it("says offline, in the user's language, for a write that never arrived", () => {
    expect(
      ledgerWriteFailureMessage(new Error("Network request failed"), i18n),
    ).toBe(i18n.t("ledgerWriteOffline"));
    expect(
      ledgerWriteFailureMessage(
        Object.assign(new Error("Response not successful"), {
          networkError: new Error("Received status code 502"),
        }),
        i18n,
      ),
    ).toBe(i18n.t("ledgerWriteOffline"));
    expect(
      ledgerWriteFailureMessage(new Error("OAuth refresh failed"), i18n),
    ).toBe(i18n.t("ledgerWriteOffline"));
  });

  it("keeps a ledger validation's own text", () => {
    const refused = Object.assign(new Error("Transaction does not balance"), {
      graphQLErrors: [
        {
          message: "Transaction does not balance",
          extensions: { code: "UNBALANCED" },
        },
      ],
    });
    expect(ledgerWriteFailureMessage(refused, i18n)).toBe(
      "Transaction does not balance",
    );
  });

  it("names rate limiting, and leaves anything else to the screen", () => {
    const limited = Object.assign(new Error("Too many requests"), {
      graphQLErrors: [
        { message: "Too many requests", extensions: { code: "RATE_LIMITED" } },
      ],
    });
    expect(ledgerWriteFailureMessage(limited, i18n)).toBe(
      i18n.t("ledgerWriteRateLimited"),
    );
    expect(
      ledgerWriteFailureMessage(new Error("Internal server error"), i18n),
    ).toBe(null);
  });

  it("returns null when there is nothing to say, so the screen's copy shows", () => {
    expect(ledgerWriteFailureMessage("boom", i18n)).toBe(null);
  });
});
