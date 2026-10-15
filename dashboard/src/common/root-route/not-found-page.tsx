import { Link } from "@tanstack/react-router";
import { Home, ArrowLeft } from "lucide-react";
import { Button } from "@/common/components/ui/button.tsx";
import { useTranslations } from "@/common/hooks/use-translations.ts";
import { PageSEO } from "@/common/components/seo/page-seo";

/**
 * 404 Not Found page component
 * Displays a modern and clean error page when a route is not found
 */
export default function NotFoundPage() {
  return (
    <NotFoundView
      titleKey="common.pageNotFound"
      descriptionKey="common.pageNotFoundDescription"
    />
  );
}

function NotFoundView({
  titleKey,
  descriptionKey,
}: {
  titleKey: string;
  descriptionKey: string;
}) {
  const { t } = useTranslations();

  const handleGoBack = () => {
    window.history.back();
  };

  return (
    <>
      <PageSEO
        titleKey="seo.notFound.title"
        descriptionKey="seo.notFound.description"
        noIndex
      />
      <main className="min-h-screen flex items-center justify-center bg-background px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-2xl text-center space-y-8">
          {/* Content Section */}
          <div className="space-y-4">
            <h1 className="text-8xl font-bold tracking-tight text-foreground">
              404
            </h1>
            <h2 className="text-3xl font-semibold text-foreground">
              {t(titleKey)}
            </h2>
            <p className="text-lg text-muted-foreground max-w-md mx-auto">
              {t(descriptionKey)}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Button
              asChild
              variant="default"
              size="lg"
              className="min-w-[140px]"
            >
              <Link to="/">
                <Home className="mr-2 h-4 w-4" />
                {t("common.goHome")}
              </Link>
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={handleGoBack}
              className="min-w-[140px]"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t("common.goBack")}
            </Button>
          </div>
        </div>
      </main>
    </>
  );
}

/** 404 for an OAuth link whose authorization parameters are missing or malformed. */
export function InvalidAuthorizationLinkPage() {
  return (
    <NotFoundView
      titleKey="common.authorizationLinkInvalid"
      descriptionKey="common.authorizationLinkInvalidDescription"
    />
  );
}

/** 404 for a ledger attachment link whose ledger or file is unavailable. */
export function AttachmentUnavailablePage() {
  return (
    <NotFoundView
      titleKey="common.attachmentUnavailable"
      descriptionKey="common.attachmentUnavailableDescription"
    />
  );
}
