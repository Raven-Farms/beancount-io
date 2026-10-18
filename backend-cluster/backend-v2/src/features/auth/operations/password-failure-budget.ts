import { createHash } from "node:crypto";
import {
  incrementInWindow,
  peekCount,
  resetCount,
} from "@/foundation/redis/redis-counter";
import { CACHE_KEYS } from "@/shared/cache";
import { RateLimitedError } from "@/shared/errors";

/**
 * How many wrong passwords one account may take in a window, from any address,
 * before password sign-in refuses it (w0/m7). Generous, so that a third party
 * cannot cheaply lock someone out; existing sessions, OAuth tokens and SSH
 * keys are unaffected, and a completed password reset clears it.
 */
export const PASSWORD_FAILURE_BUDGET = {
  max: 10,
  windowMs: 15 * 60 * 1000,
} as const;

function budgetKey(email: string): string {
  const digest = createHash("sha256")
    .update(email.trim().toLowerCase())
    .digest("hex");
  return CACHE_KEYS.auth.passwordFailuresByAccount(digest);
}

/**
 * Refuse a password attempt for an account whose budget is spent. Called
 * before the password is checked, and keyed by the email the caller typed, so
 * a known and an unknown account get the same answer. Fails open when Redis is
 * unreachable: the per-address limiters still apply.
 */
export async function assertPasswordAttemptAllowed(
  email: string,
): Promise<void> {
  const spent = await peekCount(budgetKey(email));
  if (spent && spent.count >= PASSWORD_FAILURE_BUDGET.max) {
    throw new RateLimitedError(
      Math.max(1, Math.ceil(spent.resetInMs / 1000)),
      "Too many failed sign-in attempts for this account. Try again later, or reset your password.",
    );
  }
}

/** Count a wrong password, or an email no account has. */
export async function recordPasswordFailure(email: string): Promise<void> {
  await incrementInWindow(budgetKey(email), PASSWORD_FAILURE_BUDGET.windowMs);
}

/** A correct password or a completed reset starts the account afresh. */
export async function clearPasswordFailures(email: string): Promise<void> {
  await resetCount(budgetKey(email));
}
