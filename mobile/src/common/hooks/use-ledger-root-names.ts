import { useMemo } from "react";
import { useLedgerGuard } from "@/components/ledger-guard";
import { useLedgerReadContextQuery } from "@/generated-graphql/graphql";
import type { RootNames } from "@/common/account-root";

/**
 * The guarded ledger's root names (`option "name_assets" "Activos"` …), read
 * from the cache the `LedgerGuard` already filled, so a list of rows adds no
 * requests. Empty until that read lands, which keeps Beancount's defaults.
 */
export function useLedgerRootNames(): RootNames {
  const ledgerId = useLedgerGuard();
  const { data } = useLedgerReadContextQuery({
    variables: { ledgerId },
    fetchPolicy: "cache-only",
  });
  const options = data?.getLedger.options;
  return useMemo(
    () =>
      options
        ? {
            assets: options.nameAssets,
            liabilities: options.nameLiabilities,
            equity: options.nameEquity,
            income: options.nameIncome,
            expenses: options.nameExpenses,
          }
        : {},
    [options],
  );
}
