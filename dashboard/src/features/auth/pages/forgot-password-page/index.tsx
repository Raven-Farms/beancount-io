import { Card, CardContent } from "@/common/components/ui/card";
import { PageSEO } from "@/common/components/seo/page-seo";
import { ForgotPasswordForm } from "@/features/auth/components/forgot-password-form";
import { getSafeRedirectPath } from "@/common/lib/auth/auth";

/**
 * Forgot password page component
 * Allows users to request a password reset link via email
 */
export default function ForgotPasswordPage() {
  // The route's `next`, read from the URL (validated before use).
  const next =
    typeof window === "undefined"
      ? undefined
      : (new URLSearchParams(window.location.search).get("next") ?? undefined);
  return (
    <>
      <PageSEO
        titleKey="seo.forgotPassword.title"
        descriptionKey="seo.forgotPassword.description"
      />
      <main className="min-h-screen flex items-center justify-center bg-background py-12 px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-md">
          <Card>
            <CardContent className="pt-6">
              <ForgotPasswordForm
                googleNext={getSafeRedirectPath(next) ?? "/"}
              />
            </CardContent>
          </Card>
        </div>
      </main>
    </>
  );
}
