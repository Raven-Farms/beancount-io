import { BadUserInputError, ConflictError } from "@/shared/errors";

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

/**
 * A username in the rule for a sign-up that did not choose one, derived from
 * the email's local part: lowercased, every other character mapped to `_`,
 * cut to 20, then numbered while `isTaken` says the name is in use
 * (`John.Doe+x@…` → `john_doe_x`, else `john_doe_x2`, …). Taking the local
 * part as it was let uppercase, dots, `+tags`, over-long and already-taken
 * names reach the git host (w0/046).
 */
export async function usernameFromEmail(
  email: string,
  isTaken: (username: string) => Promise<boolean>,
): Promise<string> {
  const base =
    (email.split("@")[0] ?? "")
      .toLowerCase()
      .replace(/[^a-z0-9_]/g, "_")
      .slice(0, 20) || "user";
  if (!(await isTaken(base))) return base;
  for (let n = 2; n < 10_000; n++) {
    const suffix = String(n);
    const candidate = base.slice(0, 20 - suffix.length) + suffix;
    if (!(await isTaken(candidate))) return candidate;
  }
  throw new ConflictError("Username", base);
}
