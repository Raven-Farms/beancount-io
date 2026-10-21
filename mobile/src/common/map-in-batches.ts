/**
 * `Promise.all(items.map(fn))` with at most `size` calls in flight: each
 * batch starts once the one before it settled. Results keep `items`' order.
 * Import-free so the unit runner can load it.
 */
export async function mapInBatches<T, R>(
  items: readonly T[],
  size: number,
  fn: (item: T) => Promise<R>,
): Promise<R[]> {
  const results: R[] = [];
  for (let start = 0; start < items.length; start += size) {
    results.push(
      ...(await Promise.all(items.slice(start, start + size).map(fn))),
    );
  }
  return results;
}
