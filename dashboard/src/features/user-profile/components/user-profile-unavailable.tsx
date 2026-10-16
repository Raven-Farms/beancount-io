import { Link } from "@tanstack/react-router";
import { ArrowLeft, BookOpen } from "lucide-react";
import { PageSEO } from "@/common/components/seo/page-seo";
import { Button } from "@/common/components/ui/button";
import { useTranslations } from "@/common/hooks/use-translations";
import { getErrorMessageKey } from "@/common/lib/errors/error-message";
import { EXACT_PAGE_LINK } from "@/common/lib/navigation/active-options";

export function UserProfileUnavailable({
  username,
  error,
  onRetry,
}: {
  username: string;
  error?: unknown;
  onRetry?: () => void;
}) {
  const { t } = useTranslations();
  return (
    <>
      <PageSEO
        titleKey={error ? "seo.error.title" : "userProfile.userNotFound"}
        descriptionKey={
          error ? "seo.error.description" : "userProfile.userNotFoundMessage"
        }
        params={{ username }}
        noIndex
      />
      <div className="mx-auto max-w-xl px-5 py-24 text-center">
        <BookOpen
          aria-hidden="true"
          className="mx-auto mb-6 size-10 text-muted-foreground"
        />
        <h1 className="text-2xl font-semibold">
          {t(
            error
              ? "userProfile.errorLoadingProfile"
              : "userProfile.userNotFound",
          )}
        </h1>
        <p className="mt-3 text-muted-foreground">
          {error
            ? t(getErrorMessageKey(error))
            : t("userProfile.userNotFoundMessage", { username })}
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Button variant="outline" asChild>
            <Link to="/ledger" {...EXACT_PAGE_LINK}>
              <ArrowLeft aria-hidden="true" className="size-4" />
              {t("page.dashboard.goToDashboard")}
            </Link>
          </Button>
          {onRetry && (
            <Button onClick={onRetry}>{t("userProfile.tryAgain")}</Button>
          )}
        </div>
      </div>
    </>
  );
}
