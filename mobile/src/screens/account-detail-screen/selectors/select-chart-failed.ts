/**
 * Whether the balance chart has nothing to draw because its first load failed.
 * The active report is the units one for a commodity account and the market
 * one otherwise. A failed refresh over data already loaded is not a failure to
 * draw: that chart stays, under the stale banner. Passed as a bare `error`,
 * every failed pull to refresh replaced a loaded chart with a skeleton that
 * looked like loading forever (w21/239).
 */
export function selectChartFailed({
  unitsCurrency,
  report,
  unitsReport,
}: {
  unitsCurrency: string | null | undefined;
  report: { data?: unknown; error?: unknown };
  unitsReport: { data?: unknown; error?: unknown };
}): boolean {
  const active = unitsCurrency ? unitsReport : report;
  return Boolean(active.error) && active.data == null;
}
