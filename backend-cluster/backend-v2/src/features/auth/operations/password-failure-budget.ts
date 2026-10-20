import { createHash } from "node:crypto";
import {
  reserveFailureBudget,
  completeFailureBudget,
  clearFailureBudget,
} from "@/foundation/redis/redis-admission";
import { CACHE_KEYS, TTL } from "@/shared/cache";
import { RateLimitedError, ServiceUnavailableError } from "@/shared/errors";

export const PASSWORD_FAILURE_BUDGET = {
  max: 10,
  windowMs: TTL.MIN_15,
};

function budgetKey(email: string): string {
  const digest = createHash("sha256")
    .update(email.trim().toLowerCase())
    .digest("hex");
  return CACHE_KEYS.auth.passwordFailuresByAccount(digest);
}

/** Failures and in-flight attempts share an atomic, cross-address budget. */
export async function verifyPasswordWithinBudget(
  email: string,
  verify: () => Promise<boolean>,
): Promise<boolean> {
  const key = budgetKey(email);
  const reservation = await reserveFailureBudget(
    key,
    PASSWORD_FAILURE_BUDGET.max,
    PASSWORD_FAILURE_BUDGET.windowMs,
  );
  if (!reservation)
    throw new ServiceUnavailableError("Password verification", 5);
  if (!reservation.allowed || !reservation.reservationId) {
    throw new RateLimitedError(
      Math.max(1, Math.ceil(reservation.retryAfterMs / 1000)),
      "Too many failed sign-in attempts. Try again later, or verify your email.",
      { recoveryAvailable: true },
    );
  }
  const id = reservation.reservationId;
  let verified: boolean;
  try {
    verified = await verify();
  } catch (error) {
    await completeFailureBudget(
      key,
      PASSWORD_FAILURE_BUDGET.windowMs,
      id,
      "cancel",
    );
    throw error;
  }
  const settled = await completeFailureBudget(
    key,
    PASSWORD_FAILURE_BUDGET.windowMs,
    id,
    verified ? "success" : "failure",
  );
  // A reset or expired lease invalidates this attempt, even a correct password.
  if (!settled) throw new ServiceUnavailableError("Password verification", 5);
  return verified;
}

/** A completed ownership-verified password reset ends pending attempts too. */
export async function clearPasswordFailures(email: string): Promise<void> {
  await clearFailureBudget(budgetKey(email));
}
