import { useSyncExternalStore } from "react";

const noSubscription = () => () => {};

/**
 * False on the server and during the client's hydration render, true after.
 * A component whose output depends on the browser — the current clock, the
 * local time zone — renders a deterministic form until this flips, so the
 * server markup and the first client render agree and React keeps the
 * existing nodes (and keyboard focus) instead of recovering from a mismatch.
 * A component mounted later, by client navigation, sees true immediately.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );
}
