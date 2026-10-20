import type { BeancountErrorPublic } from "@/foundation/ledger-api-types";

/**
 * Errors in `after` that `before` did not have. An error the ledger already
 * had is matched at its exact file:line first; what is left is matched by
 * message and file alone, because editing or deleting a block shifts every
 * later line — an existing error below the edit moves without being new
 * (w21/m1). Each `before` error excuses at most one `after` error, so a second
 * copy of a known message still counts as introduced.
 */
export function newLedgerErrors(
  before: readonly BeancountErrorPublic[],
  after: readonly BeancountErrorPublic[],
): BeancountErrorPublic[] {
  const file = (error: BeancountErrorPublic) =>
    `${error.message}\u0000${error.source?.filename ?? ""}`;
  const at = (error: BeancountErrorPublic) =>
    `${file(error)}:${error.source?.lineno ?? ""}`;
  const take = (counts: Map<string, number>, key: string) => {
    const left = counts.get(key) ?? 0;
    if (left > 0) counts.set(key, left - 1);
    return left > 0;
  };
  const exact = new Map<string, number>();
  before.forEach((error) =>
    exact.set(at(error), (exact.get(at(error)) ?? 0) + 1),
  );
  const unmatched = after.filter((error) => !take(exact, at(error)));
  // The before errors no exact match claimed are the ones that may have moved.
  const moved = new Map<string, number>();
  before.forEach((error) => {
    if (take(exact, at(error))) {
      moved.set(file(error), (moved.get(file(error)) ?? 0) + 1);
    }
  });
  return unmatched.filter((error) => !take(moved, file(error)));
}
