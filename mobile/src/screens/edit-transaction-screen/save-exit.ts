/**
 * Where the edit screen goes after a successful save.
 *
 * An entry's `entryHash` is content-derived (beancount `hash_entry`), so a
 * save normally changes it and the transaction-detail screen behind the editor
 * holds a dead identity. The ledger service now returns the entry's NEW hash
 * from the update; with it we can return to that detail screen and re-key it.
 *
 * A save that reports the SAME hash kept the entry's identity: the hash omits
 * `meta` and sorts postings, so a metadata edit, a comment or a reordered
 * posting does not move it (w21/251). The detail screen behind the editor is
 * still right, and refetches on focus after the write, so the editor just goes
 * back to it. Dropping to the journal there pulled the user out of the
 * transaction they were editing. With no hash reported at all (a server that
 * predates this) the safe landing is still the journal.
 */
export type SaveExit =
  | { kind: "detail"; entryHash: string }
  | { kind: "unchanged" }
  | { kind: "journal" };

export function resolveSaveExit(
  currentEntryHash: string,
  savedEntryHash: string | null | undefined,
): SaveExit {
  if (typeof savedEntryHash !== "string" || savedEntryHash.length === 0) {
    return { kind: "journal" };
  }
  return savedEntryHash === currentEntryHash
    ? { kind: "unchanged" }
    : { kind: "detail", entryHash: savedEntryHash };
}

/** What the next save must target: the entry's identity plus its checksum. */
export type SaveIdentity = { entryHash: string; sha256sum: string };

/**
 * The identity a follow-up save has to use after a successful one. The
 * checksum always moves to the saved content's; the hash moves only when the
 * server reported one (an older server echoes the request, which is the same
 * value we already hold).
 *
 * Needed when the user kept typing during the save: the screen stays put with
 * a dirty draft, and its next save must target the entry as it now exists.
 */
export function applySavedIdentity(
  current: SaveIdentity,
  payload: { entryHash?: string | null; newSha256sum: string },
): SaveIdentity {
  return {
    entryHash: payload.entryHash || current.entryHash,
    sha256sum: payload.newSha256sum,
  };
}
