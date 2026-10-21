import { isConflictError } from "../../common/ledger-conflict";
import { isEntryGone } from "../transaction-detail-screen/selectors/select-entry-gone";
import { ledgerWriteFailureMessage } from "../../common/ledger-refusal";
import type { LedgerWriteOutcome } from "../../common/ledger-write";

export type SaveFailure =
  { kind: "conflict" } | { kind: "rejected"; message: string | null };

/**
 * What Edit Transaction reports when a save is rejected. A stale checksum can
 * never succeed as it is, so it gets the reload-and-retry message; anything
 * else (invalid beancount, most often) keeps the server's own explanation,
 * which is the useful part there.
 */
export function selectSaveFailure(
  message: string | null | undefined,
): SaveFailure {
  return message && isConflictError(message)
    ? { kind: "conflict" }
    : { kind: "rejected", message: message ?? null };
}

/**
 * The failure of a save as Edit Transaction reports it. A refusal reads as
 * what the edit would break (w21/m1) — "This would add an error to your
 * ledger: …" — not the server's "Validation failed for entry: …" prose; any
 * other error keeps its own message, which is what conflict detection reads.
 */
export function selectOutcomeFailure(
  outcome: Extract<LedgerWriteOutcome, { ok: false }>,
  i18n: Parameters<typeof ledgerWriteFailureMessage>[1],
): SaveFailure {
  // An entry is addressed by a hash of its content, so one changed elsewhere
  // is answered NOT_FOUND before any checksum is compared — the same stale
  // edit a checksum conflict reports, and it gets the same Reload (w21/028).
  if (isEntryGone(outcome.error)) return { kind: "conflict" };
  return selectSaveFailure(
    ledgerWriteFailureMessage(outcome.error, i18n) ?? outcome.message,
  );
}
