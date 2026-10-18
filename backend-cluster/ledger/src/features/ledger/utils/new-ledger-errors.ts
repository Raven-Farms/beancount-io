import type { BeancountErrorPublic } from "@/foundation/ledger-api-types";

/**
 * Errors in `after` that `before` did not have, matched by message and the
 * file:line they point at. Entries are appended after a file's existing
 * content, so an error the ledger already had keeps its position and is not
 * counted again; only what the write introduces is.
 */
export function newLedgerErrors(
  before: readonly BeancountErrorPublic[],
  after: readonly BeancountErrorPublic[],
): BeancountErrorPublic[] {
  const key = (error: BeancountErrorPublic) =>
    `${error.message}\u0000${error.source?.filename ?? ""}:${error.source?.lineno ?? ""}`;
  const known = new Set(before.map(key));
  return after.filter((error) => !known.has(key(error)));
}
