import { Link, useParams } from "@tanstack/react-router";
import { GitBranch } from "lucide-react";
import { PageSEO } from "@/common/components/seo/page-seo";
import { Button } from "@/common/components/ui/button";
import { useTranslations } from "@/common/hooks/use-translations";
import { SUPPORTED_BRANCH } from "../lib/supported-branch";

/** The Files routes' 404 for a branch they cannot show (w4/281). */
export function BranchNotFound() {
  const { t } = useTranslations();
  const {
    ledgerOwner = "",
    ledgerName = "",
    branch = "",
  } = useParams({
    strict: false,
  });
  const params = { branch, main: SUPPORTED_BRANCH };

  return (
    <>
      <PageSEO
        titleKey="seo.notFound.title"
        descriptionKey="ledgerEditor.branchNotFound"
        params={params}
        noIndex
      />
      <div className="flex flex-col items-center justify-center gap-4 py-8 text-center">
        <GitBranch className="h-8 w-8 text-muted-foreground" aria-hidden />
        <p className="text-muted-foreground">
          {t("ledgerEditor.branchNotFound", params)}
        </p>
        <Button asChild>
          <Link
            to="/ledger/$ledgerOwner/$ledgerName/files/tree/$branch/$"
            params={{
              ledgerOwner,
              ledgerName,
              branch: SUPPORTED_BRANCH,
              _splat: "",
            }}
          >
            {t("ledgerEditor.browseMainFiles", params)}
          </Link>
        </Button>
      </div>
    </>
  );
}
