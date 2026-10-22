import type {
  LedgerWriteOutcome,
  LedgerWriteSpec,
} from "../../common/ledger-write";
import { isConflictError } from "../../common/ledger-conflict";
import { isEntryGone } from "./selectors/select-entry-gone";

export type DeleteTransactionDeps = {
  /** `useLedgerWrite()`'s confirm-and-return sequence. */
  confirmWrite: (spec: LedgerWriteSpec<unknown>) => Promise<LedgerWriteOutcome>;
  /** Runs the delete mutation. */
  perform: () => Promise<unknown>;
  /** The refusal in the app's words, or the server's message, or null. */
  describeFailure: (error: unknown) => string | null;
  /** A dialog the user dismisses; a toast is gone before a refusal is read. */
  showRefusal: (title: string, message: string) => void;
  /** `loading` is shown while the delete runs (w21/197). */
  messages: {
    loading?: string;
    success: string;
    failure: string;
    /** The entry changed elsewhere and was reloaded: delete it again. */
    changed?: string;
  };
  afterSuccess: () => void | Promise<void>;
  /**
   * The entry was changed or removed elsewhere, so what the screen holds is
   * stale: reload it. A gone entry then shows its removed state; a changed one
   * can be deleted again on the fresh copy (w21/250).
   */
  onStale?: (kind: StaleDelete) => void | Promise<void>;
};

/** Why a delete cannot succeed as it is: the entry moved on under it. */
export type StaleDelete = "gone" | "conflict";

/**
 * Whether a failed delete was refused because the entry changed since the
 * screen loaded it. Entries are addressed by a hash of their content, so one
 * changed elsewhere is answered NOT_FOUND before any checksum is compared; a
 * moved source slice is a conflict. Either way every retry fails the same way
 * until the entry is reloaded (w21/250).
 */
export function classifyStaleDelete(error: unknown): StaleDelete | null {
  if (isEntryGone(error)) return "gone";
  // The server's text is read to detect a stale checksum, never shown.
  return isConflictError(error instanceof Error ? error.message : "")
    ? "conflict"
    : null;
}

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
    loadingMessage: deps.messages.loading,
    successMessage: deps.messages.success,
    failureMessage: deps.messages.failure,
    failureMessageFor: (error) =>
      deps.describeFailure(error) ?? deps.messages.failure,
    afterSuccess: deps.afterSuccess,
    // An entry changed or removed elsewhere is explained by the screen's own
    // state or the dialog below; the generic toast over it read as the app
    // breaking (w21/385).
    quietFailure: (error) =>
      deps.onStale !== undefined && classifyStaleDelete(error) !== null,
  });
  if (!outcome.ok && !outcome.signedOut) {
    const stale = classifyStaleDelete(outcome.error);
    if (stale !== null && deps.onStale) {
      await deps.onStale(stale);
      // A changed entry says so and can be deleted again; a removed one needs
      // no dialog, its own screen state explains.
      if (stale === "conflict" && deps.messages.changed) {
        deps.showRefusal(deps.messages.failure, deps.messages.changed);
      }
      return false;
    }
    deps.showRefusal(deps.messages.failure, outcome.message);
  }
  return outcome.ok;
}
