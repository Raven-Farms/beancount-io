import { LedgerWriteGuard } from "@/components/ledger-write-guard";
import { MultiPostingsTransactionScreen } from "@/screens/multi-postings-transaction";
import { Stack } from "expo-router";
import { i18n } from "@/translations";

/**
 * The live add-transaction flow. Home's and Transactions' add buttons and
 * receipt capture open this route, which renders the multi-posting screen. The
 * keypad flow that used to sit beside it (`/add-transaction-legacy` and
 * `-next`) was removed: nothing linked to it, and its four defects were already
 * fixed here (w21/413).
 */
export default function AddTransaction() {
  return (
    <LedgerWriteGuard>
      <>
        <Stack.Screen options={{ title: i18n.t("multiPostingsTitle") }} />
        <MultiPostingsTransactionScreen />
      </>
    </LedgerWriteGuard>
  );
}
