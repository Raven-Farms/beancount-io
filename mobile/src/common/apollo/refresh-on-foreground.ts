/**
 * What a return to the app re-reads: every query on screen, then the readers
 * Apollo does not watch. `refetchQueries({ include: "active" })` reaches only
 * observable queries; the Home budget panel reads its actuals with one-off
 * `client.query` calls that re-run when the ledger revision changes, so a
 * spend recorded elsewhere moved Net Worth and Recent Transactions but not the
 * panel beside them (w21/225).
 *
 * Never rejects: an offline return keeps what is on screen. Free of React
 * Native and `@/` imports so the unit runner can drive it.
 */
export async function refreshOnForeground(
  client: {
    refetchQueries: (options: { include: "active" }) => Promise<unknown>;
  },
  bumpLedgerRevision: () => void,
): Promise<void> {
  try {
    await client.refetchQueries({ include: "active" });
  } catch {
    // Offline or failed: the cached data stays, and the readers below still
    // get their turn.
  } finally {
    bumpLedgerRevision();
  }
}
