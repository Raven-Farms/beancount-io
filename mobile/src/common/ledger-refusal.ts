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
 * Where an edited entry sits, for turning the server's file lines into the
 * editor's. `lineCount` is the edited text's length.
 */
type EntryLocation = {
  filename: string;
  lineno: number;
  lineCount: number;
};

/** What the screen knows about the edit that was refused. */
export type RefusalContext = {
  where?: EntryLocation;
  /** The text that was submitted. */
  draft?: string;
};

const sameFile = (cited: string, own: string) => {
  const a = cited.replace(/^\.?\//, "");
  const b = own.replace(/^\.?\//, "");
  return a === b || a.endsWith(`/${b}`) || b.endsWith(`/${a}`);
};

/**
 * The refusal's detail as a person can use it (w21/369). The server joins its
 * errors with `message (file:line)` and a parse error often repeats, so the
 * same message appears several times; each is shown once. The citation is a
 * line of the file, which the editor does not show (it numbers the entry from
 * 1): it becomes the editor's line when it falls inside the entry, and "near
 * this entry" when it does not, as it does when a stray quote runs the parser
 * into the next entry.
 */
function tidyRefusalDetail(
  detail: string,
  i18n: Translate,
  where?: EntryLocation,
): string {
  const seen = new Set<string>();
  const parts: string[] = [];
  for (const part of detail.split("; ")) {
    const text = where
      ? part.replace(/ \(([^()]+):(\d+)\)$/, (_all, file: string, line) => {
          const editorLine = Number(line) - where.lineno + 1;
          const inside =
            sameFile(file, where.filename) &&
            editorLine >= 1 &&
            editorLine <= where.lineCount;
          return ` (${
            inside
              ? i18n.t("ledgerRefusalLine", { line: String(editorLine) })
              : i18n.t("ledgerRefusalNearEntry")
          })`;
        })
      : part;
    if (seen.has(text)) continue;
    seen.add(text);
    parts.push(text);
  }
  return parts.join("; ");
}

/**
 * Whether the first line of an entry has more or fewer quotes than a header can
 * hold once escapes are set aside: a payee and a narration make at most four,
 * always in pairs. A bare quote inside the narration, or a trailing backslash
 * that escapes the closing one, ends the string early.
 */
function headerQuotesUnbalanced(draft: string): boolean {
  const header = draft.split("\n", 1)[0] ?? "";
  const quotes = (header.replace(/\\./g, "").match(/"/g) ?? []).length;
  return quotes % 2 === 1 || quotes > 4;
}

/**
 * The refusal in the app's words — "This would add an error to your ledger:
 * …" — or null, so the caller keeps its own failure copy. Takes the
 * translator rather than importing it, so jest-lite can require this file.
 */
export function describeLedgerRefusal(
  error: unknown,
  i18n: Translate,
  context: RefusalContext = {},
): string | null {
  const raw = newLedgerErrorDetail(error);
  if (!raw) return null;
  const detail = tidyRefusalDetail(raw, i18n, context.where);
  const message = i18n.t("ledgerWouldBreak", { detail });
  return context.draft !== undefined &&
    /parse error/i.test(detail) &&
    headerQuotesUnbalanced(context.draft)
    ? `${message} ${i18n.t("ledgerRefusalQuoteHint")}`
    : message;
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

/**
 * The HTTP status of a response that came back non-2xx, or null. Apollo's
 * ServerError carries `statusCode`; a thrown "Received status code N" carries
 * it in the text. A response means the server was reached, so the write may
 * have committed: "You're offline. Nothing was saved." was wrong, and invited
 * a retry that wrote a duplicate (w21/327).
 */
function responseStatus(error: unknown): number | null {
  if (typeof error !== "object" || error === null) return null;
  const candidates = [
    (error as { networkError?: unknown }).networkError,
    error,
  ];
  for (const candidate of candidates) {
    if (typeof candidate !== "object" || candidate === null) continue;
    const { statusCode, message } = candidate as {
      statusCode?: unknown;
      message?: unknown;
    };
    if (typeof statusCode === "number") return statusCode;
    const match =
      typeof message === "string"
        ? /Received status code (\d{3})/i.exec(message)
        : null;
    if (match) return Number(match[1]);
  }
  return null;
}

/** Failures raised before any write request was sent. */
const PRE_SEND_FAILURE = /OAuth refresh failed/i;

function errorText(error: unknown): string {
  const read = (candidate: unknown): string => {
    const message = (candidate as { message?: unknown } | null)?.message;
    return typeof message === "string" ? message : "";
  };
  return `${read(error)} ${read((error as { networkError?: unknown } | null)?.networkError)}`;
}

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
 * offline. Nothing was saved."); a response that was not a success (a gateway
 * 502 or 504) says the save is unconfirmed, because the write may have
 * committed; rate limiting gets its own copy. Anything
 * else is null, so the screen shows its generic failure. Transport text such
 * as "Network request failed" used to reach the screen raw, in English, under
 * copy about ledger validation (w21/117).
 */
export function ledgerWriteFailureMessage(
  error: unknown,
  i18n: Translate,
  context?: RefusalContext,
): string | null {
  const refusal = describeLedgerRefusal(error, i18n, context);
  if (refusal) return refusal;
  const codes = graphQLErrorCodes(error);
  if (codes.some((code) => LEDGER_TEXT_CODES.has(code))) {
    return error instanceof Error && error.message.trim()
      ? error.message
      : null;
  }
  if (codes.includes("RATE_LIMITED")) return i18n.t("ledgerWriteRateLimited");
  if (responseStatus(error) !== null) return i18n.t("ledgerWriteUnconfirmed");
  if (isTransportFailure(error)) {
    // A request that never left (the token refresh failed first) saved
    // nothing. Any other transport failure is also what a connection that
    // drops after the request was sent looks like, and then the write may
    // have committed: "Nothing was saved" invited a retry that wrote the entry
    // twice (w21/351).
    return i18n.t(
      PRE_SEND_FAILURE.test(errorText(error))
        ? "ledgerWriteOffline"
        : "ledgerWriteUnconfirmed",
    );
  }
  return null;
}

/**
 * Whether a write failed because the session ended under it: the server's
 * UNAUTHENTICATED, or a token refresh the server refused for good. The app
 * signs out and Welcome explains; an alert about the write on top read as a
 * raw "OAuth grant is no longer valid" (w21/119).
 */
export function isAuthTeardownError(error: unknown): boolean {
  if (graphQLErrorCodes(error).includes("UNAUTHENTICATED")) return true;
  const terminal = (candidate: unknown) =>
    typeof candidate === "object" &&
    candidate !== null &&
    (candidate as { terminal?: unknown }).terminal === true;
  return (
    terminal(error) ||
    terminal((error as { networkError?: unknown } | null)?.networkError)
  );
}
