/**
 * One merchant however its payee is spelled: trimmed and case-folded, the
 * same grouping the Merchants directory merges spellings by (w21/046).
 * Recurrence and manual marks keyed by the displayed spelling saw only part
 * of a merchant's history, and a mark was lost when the display flipped
 * (w21/169). Import-free so the unit runner can load it.
 */
export function merchantKey(payee: string): string {
  return payee.trim().toLowerCase();
}

/** Every spelling's series merged under its merchant key, by date. */
export function seriesByMerchant<T extends { date: string }>(
  seriesByPayee: ReadonlyMap<string, readonly T[]>,
): Map<string, T[]> {
  const merged = new Map<string, T[]>();
  for (const [payee, series] of seriesByPayee) {
    const key = merchantKey(payee);
    merged.set(key, [...(merged.get(key) ?? []), ...series]);
  }
  for (const series of merged.values()) {
    series.sort((a, b) => a.date.localeCompare(b.date));
  }
  return merged;
}
