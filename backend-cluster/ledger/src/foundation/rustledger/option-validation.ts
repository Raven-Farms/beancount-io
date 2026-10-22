import type { BeancountError } from "@rustledger/wasm";

/**
 * Reconcile the engine's option-value checks with Beancount's.
 *
 * Beancount's own defaults trip two of rustledger's checks, which gave a ledger
 * copied from the Beancount docs or the bean-example a permanent bell badge and
 * red error rows for options `bean-check` accepts (w21/308):
 *
 * - `[E7002] Invalid leaf account name: 'Opening-Balances'` for
 *   `option "account_previous_balances"` (and `account_rounding`,
 *   `account_current_earnings`, …). Beancount joins the value under the Equity
 *   root, so what matters is that the leaf is a valid account component: an
 *   uppercase letter or digit first, then letters, digits and hyphens. The
 *   engine rejects the hyphen. The error is dropped only when the quoted leaf IS
 *   a valid component; a genuinely bad one (`rounding`, `my rounding`) stays.
 * - `[E7007] Option 'account_rounding' is accepted for compatibility but has no
 *   effect`: a compatibility notice, not an error. It is kept, as a warning.
 *
 * Neither error carries a source line (their `code` is null; the code is a tag
 * in the message), so they are told apart by that tag, as the document checks
 * are.
 */

const INVALID_LEAF = /^\[E7002\] Invalid leaf account name: '([^']*)'/u;
const NO_EFFECT = "[E7007] Option '";

/** A valid Beancount account component, as the grammar allows it. */
const ACCOUNT_COMPONENT = /^[\p{Lu}\p{Lt}\p{Lo}\p{Nd}][\p{L}\p{M}\p{Nd}-]*$/u;

export function reconcileOptionErrors(
  errors: readonly BeancountError[],
): BeancountError[] {
  return errors.flatMap((error): BeancountError[] => {
    const leaf = INVALID_LEAF.exec(error.message)?.[1];
    if (leaf !== undefined && ACCOUNT_COMPONENT.test(leaf)) return [];
    if (error.message.startsWith(NO_EFFECT)) {
      return [{ ...error, severity: "warning" }];
    }
    return [error];
  });
}
