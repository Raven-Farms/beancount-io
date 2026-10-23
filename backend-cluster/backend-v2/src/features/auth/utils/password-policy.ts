import { ValidationError } from "@/shared/errors";

/**
 * The rule a new password is held to on sign-up and reset, after Ory Kratos's
 * validator and NIST 800-63B: a length floor, no composition rules, not too
 * close to the account's identifiers, and not a known breached password
 * (`operations/is-pwned-password.ts`). Sign-in never applies it, so a
 * password set before the rule keeps working, including one longer than the
 * 72 bytes bcrypt reads: it was truncated when stored and is compared the
 * same way. The dashboard mirrors the length bounds in
 * `features/auth/lib/password-rule.ts`.
 */
const PASSWORD_MIN_LENGTH = 8;
const PASSWORD_MAX_BYTES = 72;

/** Kratos's thresholds: closer than this edit distance is too similar… */
const MIN_IDENTIFIER_DISTANCE = 5;
/** …as is sharing a run longer than this fraction of the password. */
const MAX_SHARED_SUBSTRING_RATIO = 0.5;

const VIOLATION_TEXT = {
  MIN_LENGTH: {
    reason: `must be at least ${PASSWORD_MIN_LENGTH} characters long`,
    hint: "Use a longer password; a passphrase of a few words works well.",
  },
  MAX_LENGTH: {
    reason: `must be at most ${PASSWORD_MAX_BYTES} bytes long`,
    hint: "Use a shorter password; accented letters, non-Latin scripts and emoji take 2–4 bytes each.",
  },
  TOO_SIMILAR: {
    reason: "is too similar to the account's email or username",
    hint: "Choose a password that does not contain your email or username.",
  },
  BREACHED: {
    reason: "has appeared in a known data breach",
    hint: "Choose a password you have not used elsewhere; a password manager can generate one.",
  },
} satisfies Record<string, { reason: string; hint: string }>;

type PasswordPolicyViolation = keyof typeof VIOLATION_TEXT;

/**
 * A new password the policy refuses. `passwordPolicy` names the rule it broke
 * so clients can say which without parsing the message.
 */
export class PasswordPolicyError extends ValidationError {
  constructor(violation: PasswordPolicyViolation) {
    const { reason, hint } = VIOLATION_TEXT[violation];
    super("password", reason, hint, { passwordPolicy: violation });
  }
}

/**
 * The first local rule `password` breaks, in Kratos's order, or `null`.
 * `identifiers` are the account's email and username; empty ones are skipped.
 */
export function passwordPolicyViolation(
  password: string,
  identifiers: readonly (string | null | undefined)[],
): PasswordPolicyViolation | null {
  if (password.length < PASSWORD_MIN_LENGTH) return "MIN_LENGTH";
  if (Buffer.byteLength(password, "utf8") > PASSWORD_MAX_BYTES) {
    return "MAX_LENGTH";
  }
  const candidate = password.toLowerCase();
  for (const identifier of identifiers) {
    if (!identifier) continue;
    const id = identifier.toLowerCase();
    if (
      levenshtein(id, candidate) < MIN_IDENTIFIER_DISTANCE ||
      longestCommonSubstring(id, candidate) / candidate.length >
        MAX_SHARED_SUBSTRING_RATIO
    ) {
      return "TOO_SIMILAR";
    }
  }
  return null;
}

/** Edits (insert, delete, substitute) that turn `a` into `b`. */
function levenshtein(a: string, b: string): number {
  let previous = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const current = [i];
    for (let j = 1; j <= b.length; j++) {
      current[j] = Math.min(
        previous[j] + 1,
        current[j - 1] + 1,
        previous[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
    }
    previous = current;
  }
  return previous[b.length];
}

/** The length of the longest run of characters `a` and `b` share. */
function longestCommonSubstring(a: string, b: string): number {
  let longest = 0;
  let previous = new Array<number>(b.length + 1).fill(0);
  for (let i = 1; i <= a.length; i++) {
    const current = new Array<number>(b.length + 1).fill(0);
    for (let j = 1; j <= b.length; j++) {
      if (a[i - 1] === b[j - 1]) {
        current[j] = previous[j - 1] + 1;
        longest = Math.max(longest, current[j]);
      }
    }
    previous = current;
  }
  return longest;
}
