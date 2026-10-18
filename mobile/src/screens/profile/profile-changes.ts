import { graphQLErrorCodes } from "../../common/graphql-error-codes";

export type ProfileValues = {
  firstName: string;
  lastName: string;
  username: string;
};

export type ProfileChanges = {
  /** Both names together: the API clears a name it isn't sent. */
  name?: { firstName: string; lastName: string };
  username?: string;
};

function trimProfile(values: ProfileValues): ProfileValues {
  return {
    firstName: values.firstName.trim(),
    lastName: values.lastName.trim(),
    username: values.username.trim(),
  };
}

/** The writes a save needs: nothing for untouched fields, so renaming
 * yourself never also renames your ledgers' owner. */
export function profileChanges(
  saved: ProfileValues,
  edited: ProfileValues,
): ProfileChanges {
  const before = trimProfile(saved);
  const after = trimProfile(edited);
  const changes: ProfileChanges = {};
  if (
    before.firstName !== after.firstName ||
    before.lastName !== after.lastName
  ) {
    changes.name = { firstName: after.firstName, lastName: after.lastName };
  }
  if (before.username !== after.username) {
    changes.username = after.username;
  }
  return changes;
}

/**
 * Sign-up's username rule, which the API also enforces on a rename: 1–20
 * lowercase letters a–z, digits and underscores (w0/036).
 */
const USERNAME_PATTERN = /^[a-z0-9_]{1,20}$/;

/**
 * Whether the edited username may be saved. An unchanged name always may, so
 * an account whose name predates the rule can still save its other fields;
 * a new name must follow the rule.
 */
export function usernameAllowed(saved: string, edited: string): boolean {
  const name = edited.trim();
  return name === saved.trim() || USERNAME_PATTERN.test(name);
}

/** The field message for a refused rename, or null for a non-field failure:
 * `CONFLICT` is a taken name, `BAD_USER_INPUT` one outside the rule. Only the
 * typed code decides, never message text. */
export function usernameErrorKey(
  error: unknown,
): "profileUsernameTaken" | "profileUsernameRule" | null {
  const codes = graphQLErrorCodes(error);
  if (codes.includes("CONFLICT")) return "profileUsernameTaken";
  if (codes.includes("BAD_USER_INPUT")) return "profileUsernameRule";
  return null;
}
