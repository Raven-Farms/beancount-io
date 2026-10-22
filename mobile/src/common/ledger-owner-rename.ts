/**
 * A ledger id is `owner/name`, and renaming the account renames the owner of
 * every ledger it holds. The id the app remembers (the selected ledger, Recent
 * accounts, merchant marks) then names a ledger that no longer exists, and the
 * server answers FORBIDDEN for it (w21/226). These rewrite the old owner to the
 * new one; an id under another owner (a shared ledger) is left alone.
 */
export function renamedLedgerId(
  ledgerId: string,
  oldOwner: string,
  newOwner: string,
): string {
  const prefix = `${oldOwner}/`;
  return oldOwner && ledgerId.startsWith(prefix)
    ? `${newOwner}/${ledgerId.slice(prefix.length)}`
    : ledgerId;
}

/** A record keyed by ledger id, re-keyed for the renamed owner. */
export function renameLedgerKeys<T>(
  record: Readonly<Record<string, T>>,
  oldOwner: string,
  newOwner: string,
): Record<string, T> {
  return Object.fromEntries(
    Object.entries(record).map(([ledgerId, value]) => [
      renamedLedgerId(ledgerId, oldOwner, newOwner),
      value,
    ]),
  );
}

/**
 * A value stored with the ledger it was meant for (the Transactions filters),
 * moved to the renamed owner. Readers drop it when its ledger is not the
 * selected one, so left behind it vanished with no message (w21/644).
 */
export function renamedLedgerScope<T extends { ledgerId: string | null }>(
  scoped: T,
  oldOwner: string,
  newOwner: string,
): T {
  if (scoped.ledgerId === null) return scoped;
  const ledgerId = renamedLedgerId(scoped.ledgerId, oldOwner, newOwner);
  return ledgerId === scoped.ledgerId ? scoped : { ...scoped, ledgerId };
}
