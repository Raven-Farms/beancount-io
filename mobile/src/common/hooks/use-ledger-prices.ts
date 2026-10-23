import {
  useLedgerManagedPricesQuery,
  useLedgerPricesQuery,
} from "@/generated-graphql/graphql";

/**
 * The dates of every price the ledger holds, per commodity pair. A balance
 * valued at market reads from it which holdings had a price and how old that
 * price is (see `selectValuation`).
 */
export const useLedgerPrices = (ledgerId: string) => {
  // The client default (`cache-and-network`, then `cache-first`): prices
  // change outside the app — on the web, by the CLI, by a feed — and a
  // pinned `cache-first` kept a cold start's price-age caption on a price
  // the ledger no longer held, beside a value read from the fresh one
  // (w21/047, the residual of w21/006).
  const { loading, data, error, refetch } = useLedgerPricesQuery({
    variables: { ledgerId },
    skip: !ledgerId,
  });
  // Which of those prices come from a managed feed, judged on the feed's own
  // terms. Never gates the screen: without it every price is judged by the
  // ledger's own cadence. Same policy, and evicted with it on writes.
  const managed = useLedgerManagedPricesQuery({
    variables: { ledgerId },
    skip: !ledgerId,
  });
  return {
    loading,
    prices: data?.getLedgerCommodities,
    managed: managed.data?.getLedgerManagedPrices,
    data,
    error,
    refetch: () => Promise.all([refetch(), managed.refetch()]),
  };
};
