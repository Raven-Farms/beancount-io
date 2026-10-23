import { createPersistentVar } from "@/common/apollo/persistent-var";
import { merchantKey } from "@/common/merchant-key";
import type { RecurringOverride } from "@/screens/merchants-screen/selectors/resolve-recurring";

export type { RecurringOverride };

/**
 * Manual recurring / not-recurring choices for merchants, keyed by ledger then
 * payee. Device-local display preference (same class as theme/locale) — never
 * written to the ledger. Detection is pure derived state; an override always
 * beats it when present (see `resolveRecurringVerdict`).
 */

/** ledgerId → payee → override */
export type MerchantRecurringOverrides = Record<
  string,
  Record<string, RecurringOverride>
>;

export const [
  merchantRecurringOverridesVar,
  loadMerchantRecurringOverrides,
  flushMerchantRecurringOverrides,
] = createPersistentVar<MerchantRecurringOverrides>(
  "merchantRecurringOverrides",
  {},
);

/**
 * A ledger's marks without any for this merchant, whichever spelling they
 * were saved under: marks were keyed by the displayed spelling, which flips
 * when another spelling gains the majority (w21/169).
 */
function withoutMerchant(
  forLedger: Record<string, RecurringOverride>,
  payee: string,
): Record<string, RecurringOverride> {
  const key = merchantKey(payee);
  return Object.fromEntries(
    Object.entries(forLedger).filter(([saved]) => merchantKey(saved) !== key),
  );
}

function setRecurringOverride(
  ledgerId: string,
  payee: string,
  override: RecurringOverride,
): void {
  const current = merchantRecurringOverridesVar();
  merchantRecurringOverridesVar({
    ...current,
    [ledgerId]: {
      ...withoutMerchant(current[ledgerId] ?? {}, payee),
      [merchantKey(payee)]: override,
    },
  });
}

function clearRecurringOverride(ledgerId: string, payee: string): void {
  const current = merchantRecurringOverridesVar();
  const forLedger = current[ledgerId];
  if (!forLedger || overrideFor(current, ledgerId, payee) === null) {
    return;
  }
  const nextLedger = withoutMerchant(forLedger, payee);
  const next: MerchantRecurringOverrides = { ...current };
  if (Object.keys(nextLedger).length === 0) {
    delete next[ledgerId];
  } else {
    next[ledgerId] = nextLedger;
  }
  merchantRecurringOverridesVar(next);
}

export function overrideFor(
  overrides: MerchantRecurringOverrides,
  ledgerId: string,
  payee: string,
): RecurringOverride | null {
  const forLedger = overrides[ledgerId];
  if (!forLedger) return null;
  const key = merchantKey(payee);
  // Saved under the key, or under a spelling from before marks were keyed.
  return (
    forLedger[key] ??
    Object.entries(forLedger).find(
      ([saved]) => merchantKey(saved) === key,
    )?.[1] ??
    null
  );
}

/**
 * Toggle helper for the merchant-view control: mark recurring when off,
 * mark not-recurring when detection would otherwise pin it, clear when the
 * user undoes a manual mark that matches detection.
 */
export function toggleRecurringOverride(
  ledgerId: string,
  payee: string,
  currentlyRecurring: boolean,
  detected: boolean,
): void {
  if (!currentlyRecurring) {
    setRecurringOverride(ledgerId, payee, "recurring");
    return;
  }
  if (detected) {
    setRecurringOverride(ledgerId, payee, "notRecurring");
    return;
  }
  clearRecurringOverride(ledgerId, payee);
}
