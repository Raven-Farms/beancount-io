import { isConflictError } from "../../common/ledger-conflict";
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
  return selectSaveFailure(
    ledgerWriteFailureMessage(outcome.error, i18n) ?? outcome.message,
  );
}
