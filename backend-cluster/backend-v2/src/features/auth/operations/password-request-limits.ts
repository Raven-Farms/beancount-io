import { createHash } from "node:crypto";
import { consumeSlidingWindows } from "@/foundation/redis/redis-admission";
import { RateLimitedError, ServiceUnavailableError } from "@/shared/errors";
import { CACHE_KEYS, TTL } from "@/shared/cache";

/** Every password attempt spends these quotas, including successful sign-ins. */
export async function enforcePasswordRequestLimits(
  email: string,
  ip: string,
): Promise<void> {
  const address = createHash("sha256").update(ip).digest("hex");
  const account = createHash("sha256")
    .update(email.trim().toLowerCase())
    .digest("hex");
  // Charge the source before allocating caller-controlled account keys.
  for (const buckets of [
    [
      {
        key: CACHE_KEYS.auth.passwordRequests("ip", address, TTL.MIN_1),
        max: 60,
        windowMs: TTL.MIN_1,
      },
      {
        key: CACHE_KEYS.auth.passwordRequests("ip", address, TTL.HOUR_1),
        max: 300,
        windowMs: TTL.HOUR_1,
      },
    ],
    [
      {
        key: CACHE_KEYS.auth.passwordRequests("email", account, TTL.MIN_1),
        max: 30,
        windowMs: TTL.MIN_1,
      },
      {
        key: CACHE_KEYS.auth.passwordRequests("email", account, TTL.HOUR_1),
        max: 120,
        windowMs: TTL.HOUR_1,
      },
      {
        key: CACHE_KEYS.auth.passwordRequests(
          "pair",
          `${address}:${account}`,
          TTL.MIN_1,
        ),
        max: 10,
        windowMs: TTL.MIN_1,
      },
    ],
  ]) {
    const decision = await consumeSlidingWindows(buckets);
    if (!decision)
      throw new ServiceUnavailableError("Password verification", 5);
    if (!decision.allowed) {
      throw new RateLimitedError(
        Math.max(1, Math.ceil(decision.retryAfterMs / 1000)),
        "Too many sign-in attempts. Please try again later.",
      );
    }
  }
}
