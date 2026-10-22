import {
  graphQLErrorCodes,
  graphQLErrorExtensions,
} from "./graphql-error-codes";

/**
 * Whether a message says the ledger moved underneath a save: the checksum
 * (`sha`, `sha256sum`) it was made against no longer matches, or the server
 * reports a conflict or an HTTP 409. Whole words only: a substring test read
 * an account named `Shares`, an amount of 409.00 and a line `main.bean:1409` as
 * a conflict, and a refused write was reported as "changed elsewhere"
 * (w21/387). Shared by the editors that save against an optimistic lock.
 */
export function isConflictError(message: string): boolean {
  return (
    /\bsha(?:256(?:sum)?)?\b/i.test(message) ||
    /\bconflict\b/i.test(message) ||
    /\b(?:http|status(?:\s+code)?)\s*409\b/i.test(message)
  );
}

/**
 * Whether a failed write lost the race to another writer: the server's
 * `CONFLICT` code, or the optimistic-lock text of an older server that has no
 * such status (w21/380). A refusal the server explained (it would add a ledger
 * error) is never a conflict, whatever its text names. Reads the error to
 * classify it, never to show it.
 */
export function isConflictFailure(error: unknown): boolean {
  const codes = graphQLErrorCodes(error);
  if (
    codes.includes("VALIDATION_FAILED") ||
    codes.includes("UNBALANCED") ||
    graphQLErrorExtensions(error).some(
      ({ newLedgerErrors }) => typeof newLedgerErrors === "string",
    )
  ) {
    return false;
  }
  return (
    codes.includes("CONFLICT") ||
    isConflictError(error instanceof Error ? error.message : "")
  );
}
