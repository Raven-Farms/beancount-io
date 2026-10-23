import type { DefaultOptions } from "@apollo/client";

/**
 * Every watched query revalidates by default. The cache is persisted and
 * restored before first render (`cache-persist.ts`), so Apollo's own
 * `cache-first` default meant a cold start never asked the network: a screen
 * kept the last session's rows while Home, pinned to this policy, showed the
 * entries an agent or the CLI had written since (w21/006). Cached data still
 * renders at once, offline included. A call site that must skip the cache
 * says so (`network-only`, `no-cache`).
 */
export const APOLLO_DEFAULT_OPTIONS: DefaultOptions = {
  watchQuery: {
    fetchPolicy: "cache-and-network",
    // Revalidate once per mount (or variables change), then follow the
    // cache: later cache writes must not send every watcher back to the
    // network. `refetch` and ledger invalidation still go to the server.
    nextFetchPolicy: "cache-first",
  },
};
