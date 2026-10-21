/**
 * Decides when a return to the app refreshes what is on screen. Each screen
 * revalidates once per mount (`default-options.ts`), but tabs stay mounted for
 * the whole session: after a change made by an agent, the CLI or the web,
 * Home kept a removed transaction and the old net worth while a tab mounted
 * later showed the current ledger (w21/024).
 *
 * Refreshes on a return to `active` from the background or inactive, at most
 * once per `minIntervalMs`, so rapid app switching sends one refetch. Free of
 * React Native and `@/` imports so the unit runner can drive it.
 */
export function createForegroundRefresher({
  refresh,
  now = Date.now,
  minIntervalMs = 30_000,
}: {
  refresh: () => void;
  now?: () => number;
  minIntervalMs?: number;
}): (nextState: string) => void {
  let previous = "active";
  let lastRefresh = Number.NEGATIVE_INFINITY;
  return (nextState) => {
    const returned = nextState === "active" && previous !== "active";
    previous = nextState;
    if (!returned) return;
    const at = now();
    if (at - lastRefresh < minIntervalMs) return;
    lastRefresh = at;
    refresh();
  };
}
