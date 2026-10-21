import type { BeancountErrorPublic } from "@/foundation/ledger-api-types";
import { NewLedgerErrorsError, type LedgerWriteAction } from "@/shared/errors";

/**
 * Errors in `after` that `before` did not have, matched by message and file
 * but not line: editing or deleting a block shifts every later line, so an
 * existing error below the edit moves without being new (w21/m1). Each
 * `before` error excuses one `after` error, in order, so a second copy of a
 * known message still counts as introduced.
 */
export function newLedgerErrors(
  before: readonly BeancountErrorPublic[],
  after: readonly BeancountErrorPublic[],
): BeancountErrorPublic[] {
  const key = (error: BeancountErrorPublic) =>
    `${error.message}\u0000${error.source?.filename ?? ""}`;
  const left = new Map<string, number>();
  for (const error of before) {
    left.set(key(error), (left.get(key(error)) ?? 0) + 1);
  }
  return after.filter((error) => {
    // A warning is not an error `bean-check` would refuse (w21/188).
    if (error.severity === "warning") return false;
    const count = left.get(key(error)) ?? 0;
    if (count > 0) left.set(key(error), count - 1);
    return count === 0;
  });
}

/**
 * Refuse a write whose projection (`after`) has errors the ledger did not
 * have. Every structured write — add, edit, delete — goes through here (w0/m2,
 * w21/m1). `before` is read only when the projection has errors at all: a
 * clean projection adds nothing, and today's errors cost a second parse.
 */
export async function refuseNewLedgerErrors(
  after: readonly BeancountErrorPublic[],
  before: () => Promise<readonly BeancountErrorPublic[]>,
  action: LedgerWriteAction,
): Promise<void> {
  if (after.every((error) => error.severity === "warning")) return;
  const introduced = newLedgerErrors(await before(), after);
  if (introduced.length > 0) {
    throw new NewLedgerErrorsError(introduced, action);
  }
}
