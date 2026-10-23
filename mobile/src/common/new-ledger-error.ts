/** One entry of `getLedgerErrors`, as `useLedgerErrors` returns it. */
export type LedgerError = {
  filename: string | null | undefined;
  lineno: number | null | undefined;
  message: string;
  /** The engine's own remediation hint, when it has one (w21/424). */
  hint?: string | null;
};

/** The engine's fix hint for an error, or null when it gave none (w21/424). */
export function errorHint(error: { hint?: string | null }): string | null {
  const hint = error.hint?.trim();
  return hint ? hint : null;
}

/** An error's message followed by its hint, as a screen reader says it. */
export function errorMessageWithHint(error: {
  message: string;
  hint?: string | null;
}): string {
  const hint = errorHint(error);
  return hint ? `${error.message}. ${hint}` : error.message;
}

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
