import { renameTransactionFiltersOwner } from "@/screens/transactions-screen/filters/var";
import { renameLedgerKeys, renamedLedgerId } from "../ledger-owner-rename";
import { accountUsageVar } from "./account-usage";
import { ledgerVar } from "./ledger";
import { merchantRecurringOverridesVar } from "./merchant-recurring-overrides";

/**
 * Re-key everything the app remembers per ledger after the account's username
 * changed, so the selected ledger, Recent accounts, merchant marks and the
 * Transactions filters follow the renamed ledgers instead of being left on ids
 * that no longer exist and dropped (w21/226, w21/644).
 */
export function renameLedgerOwner(oldOwner: string, newOwner: string): void {
  if (!oldOwner || !newOwner || oldOwner === newOwner) return;
  const selected = ledgerVar();
  if (selected) ledgerVar(renamedLedgerId(selected, oldOwner, newOwner));
  accountUsageVar(renameLedgerKeys(accountUsageVar(), oldOwner, newOwner));
  merchantRecurringOverridesVar(
    renameLedgerKeys(merchantRecurringOverridesVar(), oldOwner, newOwner),
  );
  renameTransactionFiltersOwner(oldOwner, newOwner);
}
