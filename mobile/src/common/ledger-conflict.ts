import { graphQLErrorCodes } from "./graphql-error-codes";

/**
 * Whether a save was rejected because the ledger moved underneath it: the
 * checksum (`sha`) it was made against no longer matches, or the server reports
 * a conflict. Shared by both editors that save against an optimistic lock.
 */
export function isConflictError(message: string): boolean {
  const m = message.toLowerCase();
  return m.includes("sha") || m.includes("conflict") || m.includes("409");
}

/**
 * Whether a failed write lost the race to another writer: the server's
 * `CONFLICT` code, or the optimistic-lock text of an older server that has no
 * such status (w21/380). Reads the error to classify it, never to show it.
 */
export function isConflictFailure(error: unknown): boolean {
  return (
    graphQLErrorCodes(error).includes("CONFLICT") ||
    isConflictError(error instanceof Error ? error.message : "")
  );
}
