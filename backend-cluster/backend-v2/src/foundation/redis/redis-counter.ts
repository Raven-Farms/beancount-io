import { getRedisClient } from "./redis-utils";
import { logger } from "@/shared/logger";

const counterLogger = logger.child({ module: "redis-counter" });

/**
 * Atomic fixed-window counters, for anything that has to agree across
 * instances — today, rate limiting.
 *
 * The cache helper cannot do this job: counting through get-then-set is a
 * read-modify-write, and two instances doing it concurrently both read the same
 * number and both write it back plus one. A budget that undercounts under load
 * is a budget that fails exactly when it is needed. `INCR` is atomic in Redis,
 * so the count is correct however many processes are asking.
 */
export interface CounterResult {
  /** The count after this increment. */
  readonly count: number;
  /** Milliseconds until the window resets. */
  readonly resetInMs: number;
}

/**
 * Increment `key` within a fixed window, returning the new count.
 *
 * The expiry is set when the counter is created or lacks an expiry, so a
 * steady stream of requests cannot keep pushing the window out and turn a
 * per-minute budget into a permanent one.
 *
 * Returns `undefined` when Redis is unreachable. Ordinary request throttles
 * may fail open on that; security-sensitive callers such as OTP verification
 * can explicitly fail closed instead.
 */
export async function incrementInWindow(
  key: string,
  windowMs: number,
): Promise<CounterResult | undefined> {
  if (!Number.isSafeInteger(windowMs) || windowMs <= 0) return undefined;
  return withCounterClient(async (client) => {
    const result = (await client.eval(
      `
      local count = redis.call('INCR', KEYS[1])
      local ttl = redis.call('PTTL', KEYS[1])
      if ttl < 0 then
        redis.call('PEXPIRE', KEYS[1], ARGV[1])
        ttl = tonumber(ARGV[1])
      end
      return { count, ttl }
      `,
      { keys: [key], arguments: [String(windowMs)] },
    )) as [number, number];
    return { count: Number(result[0]), resetInMs: Number(result[1]) };
  });
}

/**
 * Read `key`'s current count without incrementing it, for budgets checked
 * before the attempt they count. `{ count: 0 }` when the counter does not exist;
 * `undefined` when Redis is unreachable.
 */
export async function peekCount(
  key: string,
): Promise<CounterResult | undefined> {
  return withCounterClient(async (client) => {
    const value = await client.get(key);
    if (value === null) return { count: 0, resetInMs: 0 };
    const ttl = await client.pTTL(key);
    return { count: Number(value) || 0, resetInMs: ttl > 0 ? ttl : 0 };
  });
}

/** Delete `key`'s counter, ending its window early. Best effort. */
export async function resetCount(key: string): Promise<void> {
  await withCounterClient((client) => client.del(key));
}

/** Run `fn` against Redis, or answer `undefined` when it is unreachable. */
async function withCounterClient<T>(
  fn: (client: NonNullable<ReturnType<typeof getRedisClient>>) => Promise<T>,
): Promise<T | undefined> {
  const client = getRedisClient();
  if (!client) return undefined;
  try {
    return await fn(client);
  } catch {
    counterLogger.error("Redis counter unavailable");
    return undefined;
  }
}
