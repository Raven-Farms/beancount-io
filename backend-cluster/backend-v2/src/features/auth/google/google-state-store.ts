import { getRedisClient } from "@/foundation/redis/redis-utils";

/**
 * One-time ceremony state for Sign in with Google, keyed by the `state` value.
 *
 * Stored in Redis so any backend instance can finish a ceremony another
 * started, and consumed with GETDEL so a state can be redeemed exactly once
 * even when two callbacks race. Fails closed: without Redis there is no
 * ceremony.
 */
export interface GoogleCeremonyRecord {
  nonce: string;
  codeVerifier: string;
  /** Already validated with getSafeRedirectPath. */
  next: string;
}

export interface GoogleStateStore {
  put(state: string, record: GoogleCeremonyRecord): Promise<void>;
  /** The record for `state`, deleting it; null if absent, expired or used. */
  consume(state: string): Promise<GoogleCeremonyRecord | null>;
}

const TTL_MS = 10 * 60 * 1000;
const key = (state: string) => `auth:google_state:${state}`;

// Upstream's bounded client exposes only EVAL (with timeouts and backpressure);
// both operations are single atomic scripts. Typed from getRedisClient so a
// change to that client fails the typecheck instead of failing at runtime.
type RedisClient = NonNullable<ReturnType<typeof getRedisClient>>;

const PUT_SCRIPT = "return redis.call('SET', KEYS[1], ARGV[1], 'PX', ARGV[2], 'NX')";
const CONSUME_SCRIPT = "return redis.call('GETDEL', KEYS[1])";

function client(): RedisClient {
  const c = getRedisClient();
  if (!c) throw new Error("Redis unavailable for Google sign-in state");
  return c;
}

export const redisGoogleStateStore: GoogleStateStore = {
  async put(state, record) {
    const ok = await client().eval(PUT_SCRIPT, {
      keys: [key(state)],
      arguments: [JSON.stringify(record), String(TTL_MS)],
    });
    if (ok !== "OK") throw new Error("Google sign-in state not stored");
  },
  async consume(state) {
    const raw = await client().eval(CONSUME_SCRIPT, {
      keys: [key(state)],
      arguments: [],
    });
    if (typeof raw !== "string") return null;
    const parsed = JSON.parse(raw) as Partial<GoogleCeremonyRecord>;
    if (
      typeof parsed.nonce !== "string" ||
      typeof parsed.codeVerifier !== "string" ||
      typeof parsed.next !== "string"
    ) {
      return null;
    }
    return {
      nonce: parsed.nonce,
      codeVerifier: parsed.codeVerifier,
      next: parsed.next,
    };
  },
};
