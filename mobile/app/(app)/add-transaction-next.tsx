import { LedgerWriteGuard } from "@/components/ledger-write-guard";
import { AddTransactionNextScreen } from "@/screens/add-transaction-screen/add-transaction-next-screen";
import { Redirect, Stack } from "expo-router";
import { i18n } from "@/translations";
import { useRouteParams } from "@/common/hooks/use-route-params";

/**
 * Parked with the keypad flow, off every UI path.
 *
 * Its only inbound navigation is the keypad on `/add-transaction-legacy`,
 * which is itself parked, so no screen a user can reach opens it. The live
 * entry flow is `/add-transaction`.
 */
export default function AddTransactionNext() {
  // The keypad always passes the amount it confirmed. Opened by URL without one
  // there is nothing to confirm, so go to the live flow instead of crashing on
  // the missing amount.
  const { currentMoney } = useRouteParams<{ currentMoney?: string }>();
  if (!currentMoney) {
    return <Redirect href="/add-transaction" />;
  }
  return (
    <LedgerWriteGuard>
      <>
        <Stack.Screen
          options={{
            title: i18n.t("addTransaction"),
          }}
        />
        <AddTransactionNextScreen />
      </>
    </LedgerWriteGuard>
  );
}
