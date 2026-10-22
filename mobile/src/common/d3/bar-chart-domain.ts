/**
 * The y-domain of the spending bar chart. It always includes zero, so every bar
 * grows from a visible baseline and a negative month reads below it. It
 * collapses to an empty range only for an empty or all-zero series, which gets
 * 0…1; any other series takes its real extent. Floored at 1 for every series, a
 * BTC or ETH ledger's 0.042 and 0.031 were slivers on a 0 to 1 axis (w21/236).
 */
export function barChartValueDomain(
  numbers: readonly number[],
): [number, number] {
  const min = Math.min(...numbers, 0);
  const max = Math.max(...numbers, 0);
  return min === 0 && max === 0 ? [0, 1] : [min, max];
}

/**
 * Whether every value of every series is exactly zero: a range with only
 * transfers or prices in it. Such a chart is empty, not a row of 2 pt bars over
 * a "$0 to $1" axis (w21/496).
 */
export function hasNoFlow(...series: readonly (readonly number[])[]): boolean {
  return series.every((values) => values.every((value) => value === 0));
}
