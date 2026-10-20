import { useNavigate, useSearch } from "@tanstack/react-router";
import { useApolloClient } from "@apollo/client/react";
import { PageSEO } from "@/common/components/seo/page-seo";
import { decodeLedgerId } from "@/common/lib/utils/encode";
import { getUserDefaultLedger } from "@/common/lib/utils/ledger-utils";
import { getSafeRedirectPath } from "@/common/lib/auth/auth";
import { hardNavigate } from "@/common/lib/navigation/hard-navigate";
import { useTranslations } from "@/common/hooks/use-translations";
import { useLoginForm } from "@/features/auth/hooks/use-login-form";
import { LoginForm } from "@/features/auth/components/login-form";
import { AuthPageLayout } from "@/features/auth/components/auth-page-layout";
import { Alert, AlertDescription } from "@/common/components/ui/alert";
import { postLegacyMobileAuthToken } from "@/common/providers/react-native-bridge-provider/legacy-auth-bridge";

/** Why "Continue with Google" sent the visitor back here (backend reason codes). */
const GOOGLE_REASON_KEYS = {
  google_unavailable: "auth.googleReason.unavailable",
  google_cancelled: "auth.googleReason.cancelled",
  google_state: "auth.googleReason.state",
  google_failed: "auth.googleReason.failed",
  google_unverified: "auth.googleReason.unverified",
  google_domain: "auth.googleReason.domain",
  google_not_allowed: "auth.googleReason.notAllowed",
  google_blocked: "auth.googleReason.blocked",
} as const;

export default function LoginPage() {
  const navigate = useNavigate();
  const search = useSearch({ from: "/auth/login/" });
  const { t } = useTranslations();
  const client = useApolloClient();

  const { onSubmit, isLoading, serverError } = useLoginForm({
    onSuccess: async (token) => {
      postLegacyMobileAuthToken(token.accessToken, "password");
      // An explicit `?next=` states the visitor's intent (e.g. the marketing
      // /pricing page mid-checkout, or requireAuth's original destination) and
      // outranks the default-ledger convenience jump. It may target a
      // cross-app page this router has no route for, so navigate the document.
      const safeNext = getSafeRedirectPath(search.next);
      if (safeNext) {
        hardNavigate(safeNext);
        return;
      }
      const defaultLedger = await getUserDefaultLedger(client);
      if (defaultLedger) {
        const { ledgerOwner, ledgerName } = decodeLedgerId(defaultLedger.id);
        void navigate({ to: `/ledger/${ledgerOwner}/${ledgerName}` });
      } else {
        void navigate({ to: "/auth/welcome" });
      }
    },
  });

  return (
    <>
      <PageSEO
        titleKey="seo.login.title"
        descriptionKey="seo.login.description"
      />
      <AuthPageLayout>
        <div className="space-y-8">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold text-foreground">
              {t("auth.welcomeBack")}
            </h1>
            <p className="text-muted-foreground">{t("auth.signInToAccount")}</p>
          </div>
          {search.reason === "expired" && (
            <Alert>
              <AlertDescription>
                {t("auth.loginSessionExpiredMessage")}
              </AlertDescription>
            </Alert>
          )}
          {search.reason && search.reason in GOOGLE_REASON_KEYS && (
            <Alert variant="destructive">
              <AlertDescription>
                {t(
                  GOOGLE_REASON_KEYS[
                    search.reason as keyof typeof GOOGLE_REASON_KEYS
                  ],
                )}
              </AlertDescription>
            </Alert>
          )}
          <LoginForm
            onSubmit={onSubmit}
            isLoading={isLoading}
            serverError={serverError}
            googleNext={getSafeRedirectPath(search.next) ?? "/"}
          />
        </div>
      </AuthPageLayout>
    </>
  );
}
