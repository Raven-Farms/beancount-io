type LedgerError = {
  message: string;
  filename?: string | null;
  lineno?: number | null;
};

/**
 * The first error a write left that the ledger did not have before, or null.
 * Compared by message and file, never line: a save that adds or removes lines
 * moves every later error without making it new. Each earlier error excuses
 * one later copy, so a second copy of a known message still counts. With no
 * snapshot from before the write there is nothing to compare, and nothing is
 * reported — a guess here would blame the user's save for old errors.
 */
export function firstNewLedgerError<T extends LedgerError>(
  before: readonly LedgerError[] | null,
  after: readonly T[] | null | undefined,
): T | null {
  if (!before || !after) return null;
  const key = (error: LedgerError) =>
    `${error.message}\u0000${error.filename ?? ""}`;
  const remaining = new Map<string, number>();
  for (const error of before) {
    remaining.set(key(error), (remaining.get(key(error)) ?? 0) + 1);
  }
  for (const error of after) {
    const left = remaining.get(key(error)) ?? 0;
    if (left === 0) return error;
    remaining.set(key(error), left - 1);
  }
  return null;
}
