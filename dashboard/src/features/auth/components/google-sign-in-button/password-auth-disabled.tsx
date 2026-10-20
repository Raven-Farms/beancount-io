import { useTranslations } from "@/common/hooks/use-translations";
import { GoogleSignInButton } from "./index";

/**
 * Shown in place of a password form when the server has password sign-in
 * turned off (AUTH_PASSWORD_ENABLED=false), with the Google button when
 * Google is offered.
 */
export function PasswordAuthDisabled({
  messageKey,
  next,
}: {
  messageKey: "auth.googleOnlySignUp" | "auth.passwordAuthDisabled";
  next?: string;
}) {
  const { t } = useTranslations();
  return (
    <div className="space-y-6">
      <p className="text-muted-foreground">{t(messageKey)}</p>
      <GoogleSignInButton next={next} />
    </div>
  );
}
