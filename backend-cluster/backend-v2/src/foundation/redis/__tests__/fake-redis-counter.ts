/**
 * An in-memory stand-in for `redis-counter` with the same fixed-window
 * semantics, for tests of budgets built on it. Import it first, and use it as
 * the module mock (Jest lets a factory reference `mock`-prefixed names):
 *
 *   import { fakeRedisCounter as mockFakeRedisCounter } from ".../fake-redis-counter";
 *   jest.mock("@/foundation/redis/redis-counter", () => mockFakeRedisCounter);
 *
 * and reach the state through `fakeRedisCounterState` to clear it or take
 * Redis down.
 */
export const fakeRedisCounterState = {
  counters: new Map<string, number>(),
  down: false,
  reset(): void {
    this.counters.clear();
    this.down = false;
  },
};

const RESET_IN_MS = 60_000;

export const fakeRedisCounter = {
  incrementInWindow: async (key: string) => {
    if (fakeRedisCounterState.down) return undefined;
    const count = (fakeRedisCounterState.counters.get(key) ?? 0) + 1;
    fakeRedisCounterState.counters.set(key, count);
    return { count, resetInMs: RESET_IN_MS };
  },
  peekCount: async (key: string) =>
    fakeRedisCounterState.down
      ? undefined
      : {
          count: fakeRedisCounterState.counters.get(key) ?? 0,
          resetInMs: RESET_IN_MS,
        },
  resetCount: async (key: string) => {
    fakeRedisCounterState.counters.delete(key);
  },
};
