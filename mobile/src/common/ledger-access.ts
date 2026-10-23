import { graphQLErrorCodes } from "./graphql-error-codes";

export function canWriteLedger(
  permissions?: { push: boolean; admin: boolean } | null,
): boolean {
  return permissions?.push === true || permissions?.admin === true;
}

/** The answers that mean the caller has lost the ledger, not the network. */
const ACCESS_LOST = new Set(["FORBIDDEN", "NOT_FOUND", "UNAUTHENTICATED"]);

/**
 * Whether the selected ledger can be written, from its permission read. A
 * refetch that fails in transit keeps the cached permissions: Apollo leaves
 * the last data and sets `error`, so returning offline used to flip the
 * editor and every write surface to read-only mid-edit (w21/151). Only an
 * answer that access is gone reads as read-only; a save made while still
 * offline fails with its own offline copy.
 */
export function selectCanWrite(read: {
  guest: boolean;
  ledgerId: string | null | undefined;
  data:
    | {
        getLedger: {
          id: string;
          permissions?: { push: boolean; admin: boolean } | null;
        };
      }
    | undefined;
  error: unknown;
}): boolean {
  if (read.guest) return false;
  if (!read.data || read.data.getLedger.id !== read.ledgerId) return false;
  if (
    read.error &&
    graphQLErrorCodes(read.error).some((code) => ACCESS_LOST.has(code))
  ) {
    return false;
  }
  return canWriteLedger(read.data.getLedger.permissions);
}
