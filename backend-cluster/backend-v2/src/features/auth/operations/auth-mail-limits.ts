import { createHash } from "node:crypto";
import { consumeSlidingWindows } from "@/foundation/redis/redis-admission";
import { CACHE_KEYS, TTL } from "@/shared/cache";
import { RateLimitedError, ServiceUnavailableError } from "@/shared/errors";

function bucket(
  purpose: string,
  subject: string,
  max: number,
  windowMs: number,
) {
  const digest = createHash("sha256").update(subject).digest("hex");
  return {
    key: CACHE_KEYS.auth.ceremonyRequests(purpose, digest, windowMs),
    max,
    windowMs,
  };
}

async function consume(buckets: ReturnType<typeof bucket>[]) {
  const decision = await consumeSlidingWindows(buckets);
  if (!decision) throw new ServiceUnavailableError("Authentication", 5);
  return decision;
}

async function enforce(buckets: ReturnType<typeof bucket>[]) {
  const decision = await consume(buckets);
  if (!decision.allowed)
    throw new RateLimitedError(
      Math.max(1, Math.ceil(decision.retryAfterMs / 1000)),
      "Too many authentication requests. Please try again later.",
    );
}

export async function enforceSignupRequestLimits(
  email: string,
  ip: string,
): Promise<void> {
  await enforce([bucket("signup-ip", ip, 10, TTL.HOUR_1)]);
  await enforce([
    bucket("signup-email", email.trim().toLowerCase(), 5, TTL.HOUR_1),
  ]);
}

/** Request volume is independent of delivery; known and unknown accounts queue alike. */
export async function enforceMailRequestLimits(
  email: string,
  ip: string,
): Promise<void> {
  await enforce([
    bucket("mail-ip", ip, 10, TTL.MIN_1),
    bucket("mail-ip", ip, 50, TTL.HOUR_1),
  ]);
  await enforce([
    bucket("mail-email", email.trim().toLowerCase(), 10, TTL.MIN_1),
  ]);
}

/** One mailbox allowance across signup, reset and recovery, before token rotation. */
export async function consumeMailDelivery(email: string): Promise<boolean> {
  const subject = email.trim().toLowerCase();
  return (
    await consume([
      bucket("mail-delivery", subject, 1, TTL.MIN_1),
      bucket("mail-delivery", subject, 5, TTL.HOUR_1),
    ])
  ).allowed;
}

export async function enforceSignupOtpIpLimits(ip: string): Promise<void> {
  await enforce([bucket("signup-otp-ip", ip, 30, TTL.MIN_10)]);
}

export async function enforceSignupOtpAccountLimits(
  email: string,
  sessionId: string,
): Promise<void> {
  await enforce([
    bucket("signup-otp-email", email.trim().toLowerCase(), 5, TTL.MIN_10),
    bucket("signup-otp-session", sessionId, 5, TTL.MIN_10),
  ]);
}

export async function enforceRecoveryProofLimits(
  challengeId: string,
  ip: string,
): Promise<void> {
  await enforce([bucket("recovery-otp-ip", ip, 30, TTL.MIN_10)]);
  await enforce([bucket("recovery-otp-challenge", challengeId, 5, TTL.MIN_10)]);
}

/** Only a consumed ownership proof may spend another account's recovery quota. */
export async function enforceVerifiedRecoveryAccountLimit(
  email: string,
): Promise<void> {
  await enforce([
    bucket(
      "recovery-verified-email",
      email.trim().toLowerCase(),
      3,
      TTL.MIN_15,
    ),
  ]);
}
