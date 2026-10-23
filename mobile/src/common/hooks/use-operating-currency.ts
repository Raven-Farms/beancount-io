import { useLedgerGuard } from "@/components/ledger-guard";
import { useLedgerReadContextQuery } from "@/generated-graphql/graphql";

/**
 * The guarded ledger's first `operating_currency`, read from the cache the
 * `LedgerGuard` already filled, so a list of rows adds no requests. Undefined
 * until that read lands, or for a ledger that declares none.
 */
export function useOperatingCurrency(): string | undefined {
  const ledgerId = useLedgerGuard();
  const { data } = useLedgerReadContextQuery({
    variables: { ledgerId },
    fetchPolicy: "cache-only",
  });
  return data?.getLedger.options.operatingCurrency[0];
}
