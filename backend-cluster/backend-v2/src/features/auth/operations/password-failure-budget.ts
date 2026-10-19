import { createHash } from "node:crypto";
import {
  incrementInWindow,
  peekCount,
  resetCount,
} from "@/foundation/redis/redis-counter";
import type { Budget } from "@/server/api/rate-limit";
import { CACHE_KEYS } from "@/shared/cache";
import { RateLimitedError } from "@/shared/errors";

/**
 * How many wrong passwords one account may take in a window, from any address,
 * before password sign-in refuses it (w0/m7). Generous, so that a third party
 * cannot cheaply lock someone out; existing sessions, OAuth tokens and SSH
 * keys are unaffected, and a completed password reset clears it.
 */
export const PASSWORD_FAILURE_BUDGET: Budget = {
  max: 10,
  windowMs: 15 * 60 * 1000,
};

function budgetKey(email: string): string {
  const digest = createHash("sha256")
    .update(email.trim().toLowerCase())
    .digest("hex");
  return CACHE_KEYS.auth.passwordFailuresByAccount(digest);
}

/**
 * Run one password attempt against the account's budget: refuse it before
 * `verify` runs when the budget is spent, count it when `verify` says no
 * (a wrong password or no such account, alike), and start the account afresh
 * when it says yes. Keyed by the email the caller typed, so a known and an
 * unknown account get the same answer. Fails open when Redis is unreachable:
 * the per-address limiters still apply.
 */
export async function verifyPasswordWithinBudget(
  email: string,
  verify: () => Promise<boolean>,
): Promise<boolean> {
  const key = budgetKey(email);
  const spent = await peekCount(key);
  if (spent && spent.count >= PASSWORD_FAILURE_BUDGET.max) {
    throw new RateLimitedError(
      Math.max(1, Math.ceil(spent.resetInMs / 1000)),
      "Too many failed sign-in attempts for this account. Try again later, or reset your password.",
    );
  }
  const verified = await verify();
  if (!verified) {
    await incrementInWindow(key, PASSWORD_FAILURE_BUDGET.windowMs);
  } else if (spent && spent.count > 0) {
    await resetCount(key);
  }
  return verified;
}

/** A completed password reset starts the account afresh. */
export async function clearPasswordFailures(email: string): Promise<void> {
  await resetCount(budgetKey(email));
}
