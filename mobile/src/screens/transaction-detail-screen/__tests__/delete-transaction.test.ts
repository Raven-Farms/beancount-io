/**
 * A delete the server refuses because it would break a balance assertion
 * (w21/m1) must leave the user on the entry with the refusal readable. The
 * toast alone lasted two seconds; the dialog stays until dismissed.
 *
 * Relative requires: the runner has no `@/` alias for value imports.
 */
import { describeLedgerRefusal } from "../../../common/ledger-refusal";
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
  t: (_key: "ledgerWouldBreak", { detail }: { detail: string }) =>
    `This would add an error to your ledger: ${detail}`,
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
    describeFailure: (error) =>
      describeLedgerRefusal(error, i18n) ??
      (error instanceof Error ? error.message : null),
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

  it("shows any other failure's own message in the dialog", async () => {
    const { run, record } = harness(async () => {
      throw new Error("Network request failed");
    });

    expect(await run).toBe(false);
    expect(record.dialogs[0]?.message).toBe("Network request failed");
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
