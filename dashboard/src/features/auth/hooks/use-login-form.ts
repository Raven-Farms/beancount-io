import { useState } from "react";
import { useMutation } from "@apollo/client/react";
import { SignInDocument } from "@/graphql/definitions";
import { useTranslations } from "@/common/hooks/use-translations";
import {
  getErrorMessageKey,
  useErrorMessage,
} from "@/common/lib/errors/error-message";
import { isUnauthenticatedError } from "@/common/apollo/links/auth-error-link";
import { track } from "@/common/analytics";
import type { Token } from "@/common/types/token";

/**
 * The sign-in-specific message for a refused password sign-in, or null for one
 * the shared error messages describe. UNAUTHENTICATED here means rejected
 * credentials, not an expired session. RATE_LIMITED is usually the account's
 * wrong-password budget (w0/m7), so say how to get out, not just "wait a
 * moment".
 */
export function signInRefusalKey(
  err: unknown,
): "auth.loginFailed" | "auth.loginRateLimited" | null {
  if (isUnauthenticatedError(err)) return "auth.loginFailed";
  if (getErrorMessageKey(err) === "common.errors.rateLimited") {
    return "auth.loginRateLimited";
  }
  return null;
}

type UseLoginFormOptions = {
  onSuccess: (token: Token) => void | Promise<void>;
};

export function useLoginForm({ onSuccess }: UseLoginFormOptions) {
  const { t } = useTranslations();
  const formatError = useErrorMessage();
  const [serverError, setServerError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [signIn] = useMutation(SignInDocument);

  const onSubmit = async (data: { email: string; password: string }) => {
    setServerError("");
    setIsLoading(true);
    try {
      const result = await signIn({
        variables: { email: data.email, password: data.password },
      });
      if (result.data) {
        track("login", { method: "password" });
        const token: Token = {
          accessToken: result.data.signIn.token,
          expiresAt: result.data.signIn.expireAt,
        };
        await onSuccess(token);
      } else {
        setServerError(t("auth.loginFailed"));
      }
    } catch (err: unknown) {
      const key = signInRefusalKey(err);
      setServerError(key ? t(key) : formatError(err));
    } finally {
      setIsLoading(false);
    }
  };

  return { onSubmit, isLoading, serverError };
}
