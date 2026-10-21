/**
 * A delete the server refuses because it would break a balance assertion
 * (w21/m1) must leave the user on the entry with the refusal readable. The
 * toast alone lasted two seconds; the dialog stays until dismissed.
 *
 * Relative requires: the runner has no `@/` alias for value imports.
 */
import {
  describeLedgerRefusal,
  ledgerWriteFailureMessage,
} from "../../../common/ledger-refusal";
import {
  runLedgerWrite,
  type LedgerWriteSpec,
} from "../../../common/ledger-write";
import { deleteTransaction } from "../delete-transaction";

const BALANCE_FAILED =
  "Balance failed for Assets:Cash: expected 49.75 USD, got 73.25 USD (main.bean:84)";
const refused = Object.assign(
  new Error(
    `Validation failed for entry: this deletion would introduce 1 new bean-check error: ${BALANCE_FAILED}`,
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
const i18n = {
  t: (key: string, params?: Record<string, string>) =>
    key === "ledgerWouldBreak"
      ? `This would add an error to your ledger: ${params?.detail}`
      : key,
};

function harness(perform: () => Promise<unknown>) {
  const record = {
    toasts: [] as string[],
    backs: 0,
    refreshed: 0,
    dialogs: [] as { title: string; message: string }[],
  };
  const run = deleteTransaction({
    confirmWrite: (spec: LedgerWriteSpec<unknown>) =>
      runLedgerWrite(
        {
          showToast: (message) => {
            record.toasts.push(message);
            return () => undefined;
          },
          haptics: { success: () => undefined, error: () => undefined },
          goBack: () => {
            record.backs += 1;
          },
          describeRefusal: (error) => describeLedgerRefusal(error, i18n),
        },
        spec,
      ),
    perform,
    describeFailure: (error) => ledgerWriteFailureMessage(error, i18n),
    showRefusal: (title, message) => record.dialogs.push({ title, message }),
    messages: {
      success: "Transaction deleted",
      failure: "Failed to delete transaction",
    },
    afterSuccess: () => {
      record.refreshed += 1;
    },
  });
  return { run, record };
}

describe("deleteTransaction", () => {
  it("keeps the entry on screen and shows a refusal in a dialog", async () => {
    const { run, record } = harness(async () => {
      throw refused;
    });

    expect(await run).toBe(false);
    expect(record.dialogs).toEqual([
      {
        title: "Failed to delete transaction",
        message: `This would add an error to your ledger: ${BALANCE_FAILED}`,
      },
    ]);
    expect(record.toasts.includes("Transaction deleted")).toBe(false);
    expect(record.backs).toBe(0);
    expect(record.refreshed).toBe(0);
  });

  // w21/117: transport text showed raw, in English, as if the ledger refused.
  it("shows a failure that never reached the ledger as offline", async () => {
    const { run, record } = harness(async () => {
      throw new Error("Network request failed");
    });

    expect(await run).toBe(false);
    expect(record.dialogs[0]?.message).toBe("ledgerWriteOffline");
  });

  it("confirms, refreshes and returns on success with no dialog", async () => {
    const { run, record } = harness(async () => ({ data: {} }));

    expect(await run).toBe(true);
    expect(record.dialogs).toEqual([]);
    expect(record.toasts.includes("Transaction deleted")).toBe(true);
    expect(record.backs).toBe(1);
    expect(record.refreshed).toBe(1);
  });
});

// w21/119: the session ended under the delete; Welcome says why, and an alert
// on top read as a raw "OAuth grant is no longer valid".
describe("deleteTransaction when the session ends", () => {
  it("shows no dialog or error toast for UNAUTHENTICATED", async () => {
    const { run, record } = harness(async () => {
      throw Object.assign(new Error("Authentication required"), {
        graphQLErrors: [
          {
            message: "Authentication required",
            extensions: { code: "UNAUTHENTICATED" },
          },
        ],
      });
    });
    expect(await run).toBe(false);
    expect(record.dialogs).toEqual([]);
    expect(record.toasts.length).toBe(0);
  });

  it("shows no dialog for a refresh the server refused for good", async () => {
    const { run, record } = harness(async () => {
      throw Object.assign(new Error("Response not successful"), {
        networkError: Object.assign(
          new Error("OAuth grant is no longer valid"),
          {
            terminal: true,
          },
        ),
      });
    });
    expect(await run).toBe(false);
    expect(record.dialogs).toEqual([]);
  });
});
