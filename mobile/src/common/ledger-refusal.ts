import {
  graphQLErrorCodes,
  graphQLErrorExtensions,
} from "./graphql-error-codes";

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

/** Translates the keys this module uses. */
type Translate = {
  t(key: string, params?: Record<string, string>): string;
};

/**
 * The refusal in the app's words — "This would add an error to your ledger:
 * …" — or null, so the caller keeps its own failure copy. Takes the
 * translator rather than importing it, so jest-lite can require this file.
 */
export function describeLedgerRefusal(
  error: unknown,
  i18n: Translate,
): string | null {
  const detail = newLedgerErrorDetail(error);
  return detail ? i18n.t("ledgerWouldBreak", { detail }) : null;
}

/** Codes whose message is the ledger's own text about the write. */
const LEDGER_TEXT_CODES = new Set([
  "VALIDATION_FAILED",
  "BAD_USER_INPUT",
  "UNBALANCED",
]);

/**
 * Transport failures that never reached the ledger: Apollo's network error,
 * a non-2xx response, or the app's own token refresh failing offline.
 */
const TRANSPORT_FAILURE =
  /Network request failed|Received status code|OAuth refresh failed|Failed to fetch/i;

function isTransportFailure(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return false;
  if ((error as { networkError?: unknown }).networkError) return true;
  const message = (error as { message?: unknown }).message;
  return typeof message === "string" && TRANSPORT_FAILURE.test(message);
}

/**
 * The inline error for a failed write, in the user's language. A refusal says
 * what it would break; a ledger validation keeps the server's text, which
 * names the problem; a write that never reached the server says so ("You're
 * offline. Nothing was saved."); rate limiting gets its own copy. Anything
 * else is null, so the screen shows its generic failure. Transport text such
 * as "Network request failed" used to reach the screen raw, in English, under
 * copy about ledger validation (w21/117).
 */
export function ledgerWriteFailureMessage(
  error: unknown,
  i18n: Translate,
): string | null {
  const refusal = describeLedgerRefusal(error, i18n);
  if (refusal) return refusal;
  const codes = graphQLErrorCodes(error);
  if (codes.some((code) => LEDGER_TEXT_CODES.has(code))) {
    return error instanceof Error && error.message.trim()
      ? error.message
      : null;
  }
  if (codes.includes("RATE_LIMITED")) return i18n.t("ledgerWriteRateLimited");
  if (isTransportFailure(error)) return i18n.t("ledgerWriteOffline");
  return null;
}
