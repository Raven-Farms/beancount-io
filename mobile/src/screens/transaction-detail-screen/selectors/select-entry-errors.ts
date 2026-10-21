type LedgerError = {
  message: string;
  filename?: string | null;
  lineno?: number | null;
};

/** Where an entry's source sits: its file, first line and source text. */
export type EntrySource = {
  filename: string;
  lineno: number;
  slice: string;
};

const sameFile = (errorFile: string, entryFile: string) => {
  const name = entryFile.split("/").pop() ?? entryFile;
  return (
    errorFile === entryFile ||
    errorFile === name ||
    errorFile.endsWith(`/${name}`) ||
    entryFile.endsWith(`/${errorFile}`)
  );
};

/**
 * The ledger errors that point into this entry's own source lines, from its
 * first line through its last posting. A transaction the ledger reports as
 * broken opened with no sign of it; the error only showed in Notifications
 * (w21/030). An error with no line can't be placed and is left out.
 */
export function selectEntryErrors<T extends LedgerError>(
  errors: readonly T[],
  source: EntrySource | null,
): T[] {
  if (!source || !source.filename || !Number.isFinite(source.lineno)) return [];
  const lines = source.slice.replace(/\n+$/, "").split("\n").length;
  const last = source.lineno + Math.max(lines, 1) - 1;
  return errors.filter(
    (error) =>
      error.filename != null &&
      error.lineno != null &&
      sameFile(error.filename, source.filename) &&
      error.lineno >= source.lineno &&
      error.lineno <= last,
  );
}
