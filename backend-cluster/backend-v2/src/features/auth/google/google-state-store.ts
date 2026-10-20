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

interface AtomicRedis {
  set(
    key: string,
    value: string,
    options: { PX: number; NX: true },
  ): Promise<unknown>;
  getDel(key: string): Promise<string | null>;
}

function client(): AtomicRedis {
  const c = getRedisClient() as unknown as AtomicRedis | null;
  if (!c) throw new Error("Redis unavailable for Google sign-in state");
  return c;
}

export const redisGoogleStateStore: GoogleStateStore = {
  async put(state, record) {
    const ok = await client().set(key(state), JSON.stringify(record), {
      PX: TTL_MS,
      NX: true,
    });
    if (ok !== "OK") throw new Error("Google sign-in state not stored");
  },
  async consume(state) {
    const raw = await client().getDel(key(state));
    if (raw === null) return null;
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
