import type { SignupPolicy } from "@/config/config";

/**
 * Who may create an account (SIGNUP_ALLOWED_EMAILS / SIGNUP_ALLOWED_DOMAINS).
 *
 * With both lists empty (the default) signup is open, as on managed
 * beancount.io. Once either is set, only an exactly listed email address, or an
 * address whose domain is exactly a listed domain (subdomains are not included),
 * may sign up. Enforced by AuthService both when a signup starts and when the
 * account is created, so every signup method goes through it.
 */
export function isSignupAllowed(
  email: string,
  policy: SignupPolicy | undefined,
): boolean {
  if (!policy) return true;
  if (policy.allowedEmails.size === 0 && policy.allowedDomains.size === 0) {
    return true;
  }
  const normalized = email.trim().toLowerCase();
  if (policy.allowedEmails.has(normalized)) return true;
  const at = normalized.indexOf("@");
  if (at <= 0 || normalized.indexOf("@", at + 1) !== -1) return false;
  return policy.allowedDomains.has(normalized.slice(at + 1));
}
