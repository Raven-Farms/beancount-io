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

type WindowBucket = { key: string; max: number; windowMs: number };
type FailureState = { failures: number[]; pending: Map<string, number> };
export const fakeRedisAdmissionState = {
  windows: new Map<string, number[]>(),
  failures: new Map<string, FailureState>(),
  down: false,
  next: 0,
  reset(): void {
    this.windows.clear();
    this.failures.clear();
    this.down = false;
    this.next = 0;
  },
};

export const fakeRedisAdmission = {
  consumeSlidingWindows: async (buckets: readonly WindowBucket[]) => {
    if (fakeRedisAdmissionState.down) return undefined;
    const now = Date.now();
    let retryAfterMs = 0;
    for (const bucket of buckets) {
      const events = (
        fakeRedisAdmissionState.windows.get(bucket.key) ?? []
      ).filter((at) => at > now - bucket.windowMs);
      fakeRedisAdmissionState.windows.set(bucket.key, events);
      if (events.length >= bucket.max)
        retryAfterMs = Math.max(
          retryAfterMs,
          events[0] + bucket.windowMs - now,
        );
    }
    if (retryAfterMs > 0) return { allowed: false, retryAfterMs };
    for (const bucket of buckets)
      fakeRedisAdmissionState.windows.get(bucket.key)!.push(now);
    return { allowed: true, retryAfterMs: 0 };
  },
  reserveFailureBudget: async (key: string, max: number, windowMs: number) => {
    if (fakeRedisAdmissionState.down) return undefined;
    const now = Date.now();
    const state = fakeRedisAdmissionState.failures.get(key) ?? {
      failures: [],
      pending: new Map<string, number>(),
    };
    state.failures = state.failures.filter((at) => at > now - windowMs);
    for (const [id, end] of state.pending)
      if (end <= now) state.pending.delete(id);
    fakeRedisAdmissionState.failures.set(key, state);
    if (state.failures.length + state.pending.size >= max) {
      const ends = [
        ...state.failures.map((at) => at + windowMs),
        ...state.pending.values(),
      ];
      return { allowed: false, retryAfterMs: Math.min(...ends) - now };
    }
    const reservationId = String(++fakeRedisAdmissionState.next);
    state.pending.set(reservationId, now + 30_000);
    return { allowed: true, retryAfterMs: 0, reservationId };
  },
  completeFailureBudget: async (
    key: string,
    _windowMs: number,
    id: string,
    outcome: "success" | "failure" | "cancel",
  ) => {
    if (fakeRedisAdmissionState.down) return undefined;
    const state = fakeRedisAdmissionState.failures.get(key);
    const end = state?.pending.get(id);
    if (!state || end === undefined) return false;
    state.pending.delete(id);
    if (end <= Date.now()) return false;
    if (outcome === "failure") state.failures.push(Date.now());
    if (outcome === "success") state.failures = [];
    return true;
  },
  clearFailureBudget: async (key: string) => {
    if (!fakeRedisAdmissionState.down)
      fakeRedisAdmissionState.failures.delete(key);
  },
};
