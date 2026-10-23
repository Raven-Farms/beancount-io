/**
 * Which branch a query-backed card renders. A first load that failed has no
 * data, and must not fall through to the card's empty state: "No transactions
 * yet" and "Quick add to show charts" are claims about the ledger that a failed
 * request cannot back. Cached data with a failed refetch stays "ready" — the
 * content on screen is still true.
 */
export type CardLoadState = "loading" | "failed" | "ready";

export function selectCardLoadState({
  loading,
  hasData,
  error,
}: {
  loading: boolean;
  hasData: boolean;
  error: unknown;
}): CardLoadState {
  if (hasData) return "ready";
  if (error) return "failed";
  return loading ? "loading" : "ready";
}

/**
 * Where the ledger's read context (its operating currency and renamed roots)
 * stands. Until it lands, `getPrimaryCurrency` falls back to "USD", so a EUR
 * ledger flashed a USD headline of 0 and "1 not in total", and on a failed
 * first load kept it with no error (w21/262): a screen holds its skeleton while
 * this is `loading` and shows the failure card when it is `failed`.
 */
export function selectReadContextState(
  data: unknown,
  error: unknown,
): CardLoadState {
  return selectCardLoadState({
    loading: data === undefined,
    hasData: data !== undefined,
    error,
  });
}
