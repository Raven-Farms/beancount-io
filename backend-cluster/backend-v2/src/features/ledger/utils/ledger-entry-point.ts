import { BadUserInputError } from "@/shared/errors";

/** The file the ledger service loads first; every other file hangs off it. */
const LEDGER_ENTRY_POINT = "main.bean";

/**
 * Refuses deleting or renaming the entry point: the commit lands, then every
 * read of the ledger fails until the file comes back (w23/031).
 */
export function assertKeepsEntryPoint(
  path: string,
  change: "deleted" | "renamed",
  field = "path",
): void {
  if (path !== LEDGER_ENTRY_POINT) return;
  throw new BadUserInputError(
    `${LEDGER_ENTRY_POINT} is the ledger's entry point and can't be ${change}`,
    field,
    "Replace its content instead: `updateLedgerFiles` with `content`, or REST `PUT` with its `sha`.",
  );
}
