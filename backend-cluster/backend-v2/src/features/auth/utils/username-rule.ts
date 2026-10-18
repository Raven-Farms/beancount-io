import { BadUserInputError } from "@/shared/errors";

/**
 * The username rule sign-up publishes (the dashboard registration form): 1–20
 * lowercase letters, digits and underscores. A username is the owner segment
 * of every ledger URL, so a rename is held to it too. Existing names that
 * predate the rule keep working; only a change is checked (w0/036).
 */
const USERNAME_PATTERN = /^[a-z0-9_]{1,20}$/;

export const USERNAME_RULE =
  "Usernames use 1–20 lowercase letters, numbers, or underscores.";

/** Refuses a username outside the rule as a field-level `BAD_USER_INPUT`. */
export function assertValidUsername(username: string): void {
  // `RegExp.test` stringifies its argument, and "undefined" fits the pattern.
  if (typeof username !== "string" || !USERNAME_PATTERN.test(username)) {
    throw new BadUserInputError(USERNAME_RULE, "username");
  }
}
