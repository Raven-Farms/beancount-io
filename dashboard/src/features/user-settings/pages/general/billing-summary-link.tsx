import { Link } from "@tanstack/react-router";
import { ArrowRight, CreditCard } from "lucide-react";
import { Card, CardContent } from "@/common/components/ui/card";
import { useTranslations } from "@/common/hooks/use-translations";
import { useUserLimits } from "@/common/hooks/use-user-limits";
import { planLabelKey } from "@/common/lib/subscription/tier-config";

/**
 * The plan in one line on Settings → General, linking to Billing. Pages that
 * still send subscribers here (the pricing page's "Manage subscription")
 * reach the plan in one click.
 */
export function BillingSummaryLink() {
  const { t } = useTranslations();
  const { tier } = useUserLimits();
  const planName = t(planLabelKey(tier));
  return (
    <Card>
      <CardContent className="flex items-center justify-between gap-4 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <CreditCard className="h-5 w-5 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <h2 className="text-sm font-semibold">
              {t("userSettings.subscription")}
            </h2>
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">{planName}</span>
              {" · "}
              {t("userSettings.manageSubscription")}
            </p>
          </div>
        </div>
        <Link
          to="/settings/billing"
          className="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-primary hover:underline"
        >
          {t("userSettings.billing")}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </CardContent>
    </Card>
  );
}
