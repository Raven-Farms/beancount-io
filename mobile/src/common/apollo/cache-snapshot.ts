/**
 * Fit the cache snapshot that is about to be saved under `maxSize`.
 *
 * `apollo3-cache-persist` answers an oversized snapshot by deleting what was
 * stored and pausing itself for good, and nothing in the app resumes it: one
 * large `getLedgerFile` read (a `main.bean` past 1 MiB) left the next offline
 * launch with no cache at all, and no save for the rest of the session
 * (w21/227). So the snapshot is trimmed instead: the biggest top-level reads
 * go first, whole, until the rest fits, and a snapshot that cannot be trimmed
 * far enough is saved empty rather than tripping the pause.
 *
 * Free of React Native imports so the unit runner can drive it.
 */
const ROOT = "ROOT_QUERY";

export function fitCacheSnapshot(snapshot: string, maxSize: number): string {
  if (snapshot.length <= maxSize) return snapshot;
  let cache: Record<string, unknown>;
  try {
    cache = JSON.parse(snapshot) as Record<string, unknown>;
  } catch {
    return "{}";
  }
  const root = cache[ROOT];
  if (typeof root !== "object" || root === null) return "{}";

  const fields = Object.entries(root as Record<string, unknown>)
    .map(([name, value]) => ({
      name,
      size: name.length + JSON.stringify(value).length + 4,
    }))
    .sort((a, b) => b.size - a.size);

  const kept = { ...(root as Record<string, unknown>) };
  let remaining = snapshot.length;
  for (const field of fields) {
    if (remaining <= maxSize) break;
    delete kept[field.name];
    remaining -= field.size;
  }
  const trimmed = JSON.stringify({ ...cache, [ROOT]: kept });
  // The estimate ignores separators; a snapshot still over the cap (mostly
  // normalized entities no root field owns) is not worth saving.
  return trimmed.length <= maxSize ? trimmed : "{}";
}
