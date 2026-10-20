import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation } from "@apollo/client/react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  RequestSignInRecoveryDocument,
  SignInWithEmailCodeDocument,
} from "@/graphql/definitions";
import { Button } from "@/common/components/ui/button";
import { Input } from "@/common/components/ui/input";
import { Label } from "@/common/components/ui/label";
import { Alert, AlertDescription } from "@/common/components/ui/alert";
import { useTranslations } from "@/common/hooks/use-translations";
import { getErrorMessageKey } from "@/common/lib/errors/error-message";
import type { Token } from "@/common/types/token";
import { track } from "@/common/analytics";
import { PasswordInput } from "@/features/auth/components/password-input";
import { ScriptRequiredNotice } from "@/features/auth/components/script-required-notice";
import { useHydrated } from "@/features/auth/lib/use-hydrated";
import { readAuthRetry } from "@/features/auth/lib/auth-retry";

type RecoveryFormData = { email: string; code: string; password: string };
type RecoveryError =
  | "auth.recoveryFailed"
  | "auth.recoveryRequestFailed"
  | "auth.recoveryUnavailable";

type SignInRecoveryProps = {
  challengeId?: string;
  initialEmail?: string;
  returnTo?: string;
  onSuccess: (token: Token) => void | Promise<void>;
  onBack: () => void;
};

/** Only explicit submit/resend actions send mail; mounting never requests it. */
export function SignInRecovery({
  challengeId,
  initialEmail,
  returnTo,
  onSuccess,
  onBack,
}: SignInRecoveryProps) {
  const { t, i18n } = useTranslations();
  const hydrated = useHydrated();
  const inFlight = useRef(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<RecoveryError | null>(null);
  const [cooldown, setCooldown] = useState<{
    at: number;
    action: "mail" | "verification";
  }>();
  const retryAt = cooldown?.at;
  const [requestMail, requestState] = useMutation(
    RequestSignInRecoveryDocument,
    {
      fetchPolicy: "no-cache",
    },
  );
  const [verifyCode, verificationState] = useMutation(
    SignInWithEmailCodeDocument,
    {
      fetchPolicy: "no-cache",
    },
  );
  const schema = useMemo(
    () =>
      z.object({
        email: z
          .string()
          .trim()
          .min(1, t("auth.emailRequired"))
          .email(t("auth.emailInvalid"))
          .transform((email) => email.toLowerCase()),
        code: challengeId
          ? z.string().regex(/^\d{6}$/, t("auth.recoveryCodeInvalid"))
          : z.string(),
        password: challengeId
          ? z
              .string()
              .min(1, t("auth.passwordRequired"))
              .max(128, t("auth.passwordMaxLength"))
          : z.string(),
      }),
    [t, challengeId],
  );
  const {
    register,
    handleSubmit,
    trigger,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<RecoveryFormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: initialEmail ?? "", code: "", password: "" },
    mode: "onBlur",
  });

  useEffect(() => {
    if (retryAt === undefined) return;
    const timer = setTimeout(
      () => setCooldown(undefined),
      Math.max(0, retryAt - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [retryAt]);

  const busy =
    isSubmitting || requestState.loading || verificationState.loading;
  const retryTime =
    retryAt === undefined
      ? undefined
      : new Intl.DateTimeFormat(i18n?.language, {
          hour: "numeric",
          minute: "2-digit",
          second: "2-digit",
        }).format(retryAt);

  const showFailure = (reason: unknown, verifying: boolean) => {
    const retry = readAuthRetry(reason);
    if (retry.retryAfter)
      setCooldown({
        at: Date.now() + retry.retryAfter * 1000,
        action: verifying ? "verification" : "mail",
      });
    setError(
      getErrorMessageKey(reason) === "common.errors.serviceUnavailable"
        ? "auth.recoveryUnavailable"
        : verifying
          ? "auth.recoveryFailed"
          : "auth.recoveryRequestFailed",
    );
  };

  const requestDelivery = async (email: string) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setError(null);
    try {
      const result = await requestMail({ variables: { email, returnTo } });
      if (result.data?.requestSignInRecovery.success) {
        setSent(true);
        setCooldown({ at: Date.now() + 60_000, action: "mail" });
      } else {
        setError("auth.recoveryRequestFailed");
      }
    } catch (reason: unknown) {
      showFailure(reason, false);
    } finally {
      inFlight.current = false;
    }
  };

  const onSubmit = handleSubmit(async (data) => {
    if (!challengeId) {
      if (!hydrated || requestState.loading || retryAt !== undefined) return;
      await requestDelivery(data.email);
      return;
    }
    if (
      !hydrated ||
      inFlight.current ||
      verificationState.loading ||
      cooldown?.action === "verification"
    )
      return;
    inFlight.current = true;
    setError(null);
    try {
      const result = await verifyCode({
        variables: {
          email: data.email,
          challengeId,
          code: data.code,
          password: data.password,
        },
      });
      const session = result.data?.signInWithEmailCode;
      if (!session) {
        setError("auth.recoveryFailed");
        return;
      }
      track("login", { method: "password" });
      await onSuccess({
        accessToken: session.token,
        expiresAt: session.expireAt,
      });
    } catch (reason: unknown) {
      showFailure(reason, true);
    } finally {
      inFlight.current = false;
    }
  });

  return (
    <form className="space-y-6" method="post" onSubmit={onSubmit} noValidate>
      <div className="space-y-2">
        <Label htmlFor="recovery-email">{t("auth.emailAddress")}</Label>
        <Input
          id="recovery-email"
          type="email"
          autoComplete="email"
          placeholder={t("auth.enterYourEmail")}
          {...register("email")}
          aria-invalid={errors.email ? true : undefined}
          aria-describedby={errors.email ? "recovery-email-error" : undefined}
        />
        {errors.email && (
          <p
            id="recovery-email-error"
            role="alert"
            className="text-sm text-destructive"
          >
            {errors.email.message}
          </p>
        )}
      </div>
      {challengeId && (
        <>
          <div className="space-y-2">
            <Label htmlFor="recovery-code">{t("auth.recoveryCode")}</Label>
            <Input
              id="recovery-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              {...register("code")}
              aria-invalid={errors.code ? true : undefined}
              aria-describedby={
                errors.code
                  ? "recovery-code-error recovery-code-help"
                  : "recovery-code-help"
              }
            />
            {errors.code && (
              <p
                id="recovery-code-error"
                role="alert"
                className="text-sm text-destructive"
              >
                {errors.code.message}
              </p>
            )}
            <p
              id="recovery-code-help"
              className="text-sm text-muted-foreground"
            >
              {t("auth.recoveryExpiry")}
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="recovery-password">{t("auth.password")}</Label>
            <PasswordInput
              id="recovery-password"
              autoComplete="current-password"
              maxLength={128}
              placeholder={t("auth.enterYourPassword")}
              {...register("password")}
              aria-invalid={errors.password ? true : undefined}
              aria-describedby={
                errors.password ? "recovery-password-error" : undefined
              }
            />
            {errors.password && (
              <p
                id="recovery-password-error"
                role="alert"
                className="text-sm text-destructive"
              >
                {errors.password.message}
              </p>
            )}
          </div>
        </>
      )}
      {sent && (
        <p role="status" className="text-sm text-muted-foreground">
          {t("auth.recoverySent")}
        </p>
      )}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{t(error)}</AlertDescription>
        </Alert>
      )}
      {retryTime && (
        <p role="status" className="text-sm text-muted-foreground">
          {t("auth.recoveryRetryAt", { time: retryTime })}
        </p>
      )}
      <ScriptRequiredNotice />
      <Button
        className="w-full"
        size="lg"
        type="submit"
        disabled={
          !hydrated ||
          busy ||
          cooldown?.action === (challengeId ? "verification" : "mail")
        }
      >
        {challengeId
          ? t(
              verificationState.loading
                ? "auth.recoveryVerifying"
                : "auth.recoverySubmit",
            )
          : t(
              requestState.loading
                ? "auth.recoverySending"
                : sent
                  ? "auth.recoveryResend"
                  : "auth.recoverySendEmail",
            )}
      </Button>
      {challengeId && (
        <Button
          className="w-full"
          variant="outline"
          type="button"
          disabled={!hydrated || busy || cooldown?.action === "mail"}
          onClick={async () => {
            if (!hydrated || inFlight.current || cooldown?.action === "mail")
              return;
            if (await trigger("email"))
              await requestDelivery(getValues("email").trim().toLowerCase());
          }}
        >
          {t(
            requestState.loading
              ? "auth.recoverySending"
              : "auth.recoveryResend",
          )}
        </Button>
      )}
      <Button
        className="w-full"
        variant="link"
        type="button"
        disabled={busy}
        onClick={onBack}
      >
        {t("auth.backToSignIn")}
      </Button>
    </form>
  );
}
