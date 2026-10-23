import { randomUUID } from "node:crypto";
import { TTL } from "@/shared/cache/cache-ttl";
import { logger } from "@/shared/logger";
import { getRedisClient } from "./redis-utils";

const admissionLogger = logger.child({ module: "redis-admission" });
// A crashed verifier must release its slot. A verifier finishing after its lease
// must reject the result instead of authenticating without a reservation.
const RESERVATION_LEASE_MS = TTL.SEC_30;

const SLIDING_WINDOWS = `
local time = redis.call('TIME')
local now = tonumber(time[1]) * 1000 + math.floor(tonumber(time[2]) / 1000)
local retry = 0
for i, key in ipairs(KEYS) do
  local max = tonumber(ARGV[i * 2])
  local window = tonumber(ARGV[i * 2 + 1])
  redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
  local count = redis.call('ZCARD', key)
  if count >= max then
    local oldest = redis.call('ZRANGE', key, count - max, count - max, 'WITHSCORES')
    retry = math.max(retry, tonumber(oldest[2]) + window - now)
  end
end
if retry > 0 then return {0, retry} end
for i, key in ipairs(KEYS) do
  redis.call('ZADD', key, now, ARGV[1])
  redis.call('PEXPIRE', key, ARGV[i * 2 + 1])
end
return {1, 0}
`;

// Both sets store expiration instants as scores. Failed attempts and live
// verifiers share one budget, so concurrent requests cannot all pass the check.
const RESERVE_FAILURE = `
local time = redis.call('TIME')
local now = tonumber(time[1]) * 1000 + math.floor(tonumber(time[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
local failures = redis.call('ZCARD', KEYS[1])
local pending = redis.call('ZCARD', KEYS[2])
if failures + pending >= tonumber(ARGV[1]) then
  local firstFailure = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
  local firstPending = redis.call('ZRANGE', KEYS[2], 0, 0, 'WITHSCORES')
  local first = math.min(tonumber(firstFailure[2]) or math.huge,
                         tonumber(firstPending[2]) or math.huge)
  return {0, first - now}
end
redis.call('ZADD', KEYS[2], now + tonumber(ARGV[2]), ARGV[3])
redis.call('PEXPIRE', KEYS[2], ARGV[2])
return {1, 0}
`;

const COMPLETE_FAILURE = `
local time = redis.call('TIME')
local now = tonumber(time[1]) * 1000 + math.floor(tonumber(time[2]) / 1000)
local expires = redis.call('ZSCORE', KEYS[2], ARGV[1])
redis.call('ZREM', KEYS[2], ARGV[1])
if not expires or tonumber(expires) <= now then return 0 end
if ARGV[3] == 'failure' then
  redis.call('ZADD', KEYS[1], now + tonumber(ARGV[2]), ARGV[1])
  redis.call('PEXPIRE', KEYS[1], ARGV[2])
elseif ARGV[3] == 'success' then
  redis.call('DEL', KEYS[1])
end
return 1
`;

interface AdmissionResult {
  readonly allowed: boolean;
  readonly retryAfterMs: number;
}

/** Atomically consume all rolling budgets, or consume none. Redis failure is
 * distinct from a rejection, so security-sensitive callers can return 503. */
export async function consumeSlidingWindows(
  buckets: readonly { key: string; max: number; windowMs: number }[],
): Promise<AdmissionResult | undefined> {
  if (buckets.length === 0) return { allowed: true, retryAfterMs: 0 };
  const keys = buckets.map((bucket) => bucket.key);
  if (new Set(keys).size !== keys.length) {
    throw new RangeError("Admission buckets must have distinct keys");
  }
  for (const bucket of buckets) validateBudget(bucket.max, bucket.windowMs);
  const result = await evaluate(SLIDING_WINDOWS, keys, [
    randomUUID(),
    ...buckets.flatMap(({ max, windowMs }) => [String(max), String(windowMs)]),
  ]);
  return readAdmission(result);
}

/** Reserve before verifying a password; failure consumes the reservation and
 * success clears failures, without releasing other in-flight verifiers. */
export async function reserveFailureBudget(
  key: string,
  max: number,
  windowMs: number,
): Promise<
  (AdmissionResult & { readonly reservationId?: string }) | undefined
> {
  validateBudget(max, windowMs);
  const reservationId = randomUUID();
  const result = readAdmission(
    await evaluate(RESERVE_FAILURE, failureKeys(key), [
      String(max),
      String(RESERVATION_LEASE_MS),
      reservationId,
    ]),
  );
  if (!result) return undefined;
  return result.allowed ? { ...result, reservationId } : result;
}

/** Returns false for stale, cancelled, or reset reservations. In particular a
 * stale success must never be accepted as a valid authentication attempt. */
export async function completeFailureBudget(
  key: string,
  windowMs: number,
  reservationId: string,
  outcome: "success" | "failure" | "cancel",
): Promise<boolean | undefined> {
  validateBudget(1, windowMs);
  const result = await evaluate(COMPLETE_FAILURE, failureKeys(key), [
    reservationId,
    String(windowMs),
    outcome,
  ]);
  return result === undefined ? undefined : result === 1;
}

/** Invalidates pending reservations too; stale completions cannot recreate a
 * failed-attempt budget after an ownership-verified recovery. Best effort. */
export async function clearFailureBudget(key: string): Promise<void> {
  await evaluate(
    "return redis.call('DEL', KEYS[1], KEYS[2])",
    failureKeys(key),
    [],
  );
}

function failureKeys(key: string): string[] {
  return [`${key}:failures`, `${key}:pending`];
}

function validateBudget(max: number, windowMs: number): void {
  if (
    !Number.isSafeInteger(max) ||
    max <= 0 ||
    !Number.isSafeInteger(windowMs) ||
    windowMs <= 0
  ) {
    throw new RangeError(
      "Admission budget and window must be positive integers",
    );
  }
}

function readAdmission(result: unknown): AdmissionResult | undefined {
  if (!Array.isArray(result) || result.length !== 2) return undefined;
  const [allowed, retryAfterMs] = result;
  if (
    (allowed !== 0 && allowed !== 1) ||
    !Number.isSafeInteger(retryAfterMs) ||
    retryAfterMs < 0
  ) {
    return undefined;
  }
  return { allowed: allowed === 1, retryAfterMs };
}

async function evaluate(
  script: string,
  keys: string[],
  args: string[],
): Promise<unknown> {
  const client = getRedisClient();
  if (!client) return undefined;
  try {
    return await client.eval(script, { keys, arguments: args });
  } catch {
    // Redis errors may include command arguments and therefore identities. Log
    // only a static diagnosis; never log scripts, keys, or error messages.
    admissionLogger.error("Redis admission unavailable");
    return undefined;
  }
}
