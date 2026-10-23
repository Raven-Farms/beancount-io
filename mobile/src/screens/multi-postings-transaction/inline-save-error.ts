import type { LedgerWriteOutcome } from "../../common/ledger-write";

/**
 * What New Transaction shows under its postings after a save: nothing when it
 * went through, else the failure the toast flashed — for a refusal, what the
 * entry would break (w0/m2), so the reason outlives the toast (w21/001).
 */
export function inlineSaveError(outcome: LedgerWriteOutcome): string | null {
  return outcome.ok ? null : outcome.message;
}
