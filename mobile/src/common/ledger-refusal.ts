import { graphQLErrorExtensions } from "./graphql-error-codes";

/**
 * What a refused write says it would break, or null when the error is anything
 * else. The server refuses a write that would add bean-check errors — a second
 * `open` for an account already open — as `VALIDATION_FAILED`, naming each new
 * error in `extensions.newLedgerErrors` (w0/m2). That is the engine's own
 * diagnosis, the same text the ledger's error list shows.
 */
function newLedgerErrorDetail(error: unknown): string | null {
  for (const { code, newLedgerErrors } of graphQLErrorExtensions(error)) {
    if (code !== "VALIDATION_FAILED" || typeof newLedgerErrors !== "string") {
      continue;
    }
    const detail = newLedgerErrors.trim();
    if (detail) return detail;
  }
  return null;
}

/**
 * The refusal in the app's words — "This would add an error to your ledger:
 * …" — or null, so the caller keeps its own failure copy. Takes the
 * translator rather than importing it, so jest-lite can require this file.
 */
export function describeLedgerRefusal(
  error: unknown,
  i18n: { t(key: "ledgerWouldBreak", params: { detail: string }): string },
): string | null {
  const detail = newLedgerErrorDetail(error);
  return detail ? i18n.t("ledgerWouldBreak", { detail }) : null;
}

/**
 * The inline error for a failed write on a screen that shows its own: the
 * refusal in the app's words, else the error's message, else null so the
 * screen falls back to its generic copy. Open Account and Add Budget share it.
 */
export function ledgerWriteFailureMessage(
  error: unknown,
  i18n: Parameters<typeof describeLedgerRefusal>[1],
): string | null {
  return (
    describeLedgerRefusal(error, i18n) ??
    (error instanceof Error ? error.message : null)
  );
}
