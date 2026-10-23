/**
 * The line under a transaction row's name: the narration, when the name shown
 * is the payee and the narration says something else. Ledgers whose payees
 * repeat (quarterly filings, a batch name stamped by an import) otherwise list
 * rows that read alike, and a search matches text no row displays.
 */
export function entryRowSecondaryText(entry: {
  payee?: string | null;
  narration?: string | null;
}): string | null {
  const payee = entry.payee?.trim();
  const narration = entry.narration?.trim();
  if (!payee || !narration || narration === payee) return null;
  return narration;
}

/**
 * The name a transaction row shows: its payee, else its narration, else
 * nothing. Both are trimmed first: importers write a blank, padded payee as
 * spaces, which won the title and left the row with no text at all, with the
 * narration dropped from the second line too (w21/568).
 */
export function entryRowTitle(entry: {
  payee?: string | null;
  narration?: string | null;
}): string | undefined {
  return entry.payee?.trim() || entry.narration?.trim() || undefined;
}
