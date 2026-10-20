import { Button } from "@/common/components/ui/button";
import { useTranslations } from "@/common/hooks/use-translations";
import { getSafeRedirectPath } from "@/common/lib/auth/auth";
import { useAuthProviders } from "@/features/auth/hooks/use-auth-providers";

/**
 * "Continue with Google", shown only when the backend reports Google as
 * configured (GET /api-gateway/auth/providers, via useAuthProviders). Both requests go to the
 * dashboard's own origin: Google returns to DASHBOARD_URL/api-gateway/auth/
 * google/callback, so the ceremony must start on the same host for its state
 * cookie to come back. A deployment that does not serve /api-gateway/ there
 * gets no button (the probe fails), never a broken one.
 */
export function GoogleSignInButton({ next }: { next?: string }) {
  const { t } = useTranslations();
  const { google } = useAuthProviders();
  if (!google) return null;

  // Default to the page the visitor is on (e.g. an OAuth consent page), so
  // the ceremony returns them there.
  const target =
    getSafeRedirectPath(next) ??
    getSafeRedirectPath(
      typeof window === "undefined"
        ? undefined
        : `${window.location.pathname}${window.location.search}`,
    );
  const href = `/api-gateway/auth/google/start${
    target ? `?next=${encodeURIComponent(target)}` : ""
  }`;

  return (
    <Button asChild variant="outline" className="w-full" size="lg">
      <a href={href}>{t("auth.continueWithGoogle")}</a>
    </Button>
  );
}
