import { z } from "zod";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { useTranslations } from "@/common/hooks/use-translations";
import { useErrorMessage } from "@/common/lib/errors/error-message";

/**
 * backend-v2's bounds for a new password on sign-up and reset
 * (`features/auth/utils/password-policy.ts`): 8 characters to 72 UTF-8 bytes,
 * the most bcrypt reads. Sign-in is not held to them.
 */
const PASSWORD_MIN_LENGTH = 8;
const PASSWORD_MAX_BYTES = 72;
const utf8 = new TextEncoder();

/** The field rule for a password being chosen, as sign-up and reset apply it. */
export function newPasswordSchema(t: ReturnType<typeof useTranslations>["t"]) {
  return z
    .string()
    .min(1, t("auth.newPasswordRequired"))
    .min(PASSWORD_MIN_LENGTH, t("auth.newPasswordMinLength"))
    .refine(
      (password) => utf8.encode(password).length <= PASSWORD_MAX_BYTES,
      t("auth.newPasswordMaxLength"),
    );
}

const POLICY_KEYS = {
  MIN_LENGTH: "auth.newPasswordMinLength",
  MAX_LENGTH: "auth.newPasswordMaxLength",
  TOO_SIMILAR: "auth.passwordTooSimilar",
  BREACHED: "auth.passwordBreached",
} as const;

/**
 * The message key for a new password the server refused, from the rule it
 * names in `extensions.passwordPolicy`, or null for any other error. The
 * breach and similarity checks are the server's alone.
 */
export function passwordPolicyRefusalKey(
  error: unknown,
): (typeof POLICY_KEYS)[keyof typeof POLICY_KEYS] | null {
  if (!CombinedGraphQLErrors.is(error)) return null;
  for (const gqlError of error.errors) {
    const rule = gqlError.extensions?.passwordPolicy;
    if (typeof rule === "string" && Object.hasOwn(POLICY_KEYS, rule)) {
      return POLICY_KEYS[rule as keyof typeof POLICY_KEYS];
    }
  }
  return null;
}

/** `useErrorMessage`, saying which rule a refused new password broke. */
export function useNewPasswordErrorMessage(): (error: unknown) => string {
  const { t } = useTranslations();
  const formatError = useErrorMessage();
  return (error) => {
    const refusal = passwordPolicyRefusalKey(error);
    return refusal ? t(refusal) : formatError(error);
  };
}
