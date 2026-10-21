import type {
  LedgerWriteOutcome,
  LedgerWriteSpec,
} from "../../common/ledger-write";

export type DeleteTransactionDeps = {
  /** `useLedgerWrite()`'s confirm-and-return sequence. */
  confirmWrite: (spec: LedgerWriteSpec<unknown>) => Promise<LedgerWriteOutcome>;
  /** Runs the delete mutation. */
  perform: () => Promise<unknown>;
  /** The refusal in the app's words, or the server's message, or null. */
  describeFailure: (error: unknown) => string | null;
  /** A dialog the user dismisses; a toast is gone before a refusal is read. */
  showRefusal: (title: string, message: string) => void;
  messages: { success: string; failure: string };
  afterSuccess: () => void | Promise<void>;
};

/**
 * Delete the entry on the detail screen. A refused delete — one that would
 * break a balance assertion (w21/m1) — keeps the screen and the entry, and
 * says why in a dialog that stays until dismissed: the 2-second toast alone
 * was gone before a sentence-long refusal could be read.
 */
export async function deleteTransaction(
  deps: DeleteTransactionDeps,
): Promise<boolean> {
  const outcome = await deps.confirmWrite({
    perform: deps.perform,
    successMessage: deps.messages.success,
    failureMessage: deps.messages.failure,
    failureMessageFor: (error) =>
      deps.describeFailure(error) ?? deps.messages.failure,
    afterSuccess: deps.afterSuccess,
  });
  if (!outcome.ok && !outcome.signedOut) {
    deps.showRefusal(deps.messages.failure, outcome.message);
  }
  return outcome.ok;
}
