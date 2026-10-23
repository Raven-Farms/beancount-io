/**
 * One write at a time from a form (w21/044).
 *
 * New Transaction's Done stayed live through the whole `addEntries` round
 * trip — its only guard was set after the write resolved — so a second tap
 * while "Saving…" showed posted the entry twice. The gate closes
 * synchronously, before the first `await`, so two presses in the same tick
 * run the write once; it reopens when the write settles, so a failed save can
 * be retried with the draft intact.
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */
export type SingleFlight = {
  /** Whether a write is running. */
  readonly busy: () => boolean;
  /** Run `write` unless one is already running; resolves to its result or `undefined`. */
  run<T>(write: () => Promise<T>): Promise<T | undefined>;
};

export function createSingleFlight(
  onBusyChange: (busy: boolean) => void = () => undefined,
): SingleFlight {
  let running = false;
  return {
    busy: () => running,
    async run(write) {
      if (running) return undefined;
      running = true;
      onBusyChange(true);
      try {
        return await write();
      } finally {
        running = false;
        onBusyChange(false);
      }
    },
  };
}
