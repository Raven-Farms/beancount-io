/**
 * The public username rule, as backend-v2 enforces it on sign-up and rename
 * (`features/auth/utils/username-rule.ts`): 1–20 lowercase letters, digits
 * and underscores. A username is the owner segment of every ledger URL.
 */
export const USERNAME_MAX_LENGTH = 20;
export const USERNAME_CHARACTERS = /^[a-z0-9_]+$/;

/**
 * The message key for the first part of the rule `username` breaks, or
 * `null` when it fits. Settings' rename checks it before submitting, as the
 * registration form does (w0/047).
 */
export function usernameRuleError(
  username: string,
):
  | "auth.usernameRequired"
  | "auth.usernameMaxLength"
  | "auth.usernameLowercaseAlphanumeric"
  | null {
  if (username.length === 0) return "auth.usernameRequired";
  if (username.length > USERNAME_MAX_LENGTH) return "auth.usernameMaxLength";
  if (!USERNAME_CHARACTERS.test(username)) {
    return "auth.usernameLowercaseAlphanumeric";
  }
  return null;
}
