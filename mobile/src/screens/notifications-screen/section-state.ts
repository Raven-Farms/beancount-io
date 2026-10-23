/**
 * Whether each Notifications section is still waiting for its first result.
 *
 * Each section follows its own query. The errors section stays pending until
 * its query has answered, so it never says "Ledger is healthy" about a result
 * that has not arrived; an empty error list and a missing one look the same
 * once collapsed. A failed first load is no longer pending either: the section
 * shows its failure and Try again instead of a skeleton forever (w21/068).
 * Commits already on screen stay put during a refetch.
 */
export function selectSectionsPending(state: {
  errorsLoaded: boolean;
  errorsFailed: boolean;
  commitsLoading: boolean;
  commitsLoaded: boolean;
}): { errorsPending: boolean; commitsPending: boolean } {
  return {
    errorsPending: !state.errorsLoaded && !state.errorsFailed,
    commitsPending: state.commitsLoading && !state.commitsLoaded,
  };
}
