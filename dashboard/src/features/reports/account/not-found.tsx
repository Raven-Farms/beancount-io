import { Link, useParams } from "@tanstack/react-router";
import { Button } from "@/common/components/ui/button";
import { PageSEO } from "@/common/components/seo/page-seo";
import { useTranslations } from "@/common/hooks/use-translations";

export function AccountNotFound() {
  const { ledgerOwner, ledgerName, accountName } = useParams({
    from: "/ledger/$ledgerOwner/$ledgerName/account/$accountName",
  });
  const { t } = useTranslations();

  return (
    <>
      <PageSEO
        titleKey="seo.notFound.title"
        descriptionKey="page.accountReport.notFound"
        params={{ accountName }}
        noIndex
      />
      <div className="flex flex-col items-start gap-4 py-6">
        <h1 className="text-xl font-semibold">
          {t("page.accountReport.notFound", { accountName })}
        </h1>
        <Button asChild>
          <Link
            to="/ledger/$ledgerOwner/$ledgerName/accounts"
            params={{ ledgerOwner, ledgerName }}
          >
            {t("page.accounts.accounts")}
          </Link>
        </Button>
      </div>
    </>
  );
}
