import { Crown } from "lucide-react";
import { Button } from "@/common/components/ui/button";
import { Badge } from "@/common/components/ui/badge";
import type { GetSubscriptionStatusQuery } from "@/graphql/definitions";
import type { CancelTarget } from "@/features/user-settings/hooks/use-subscription-cancel";
import { isPendingCancellation } from "./subscription-state";
import { useBillingDateFormat, useMoneyFormat } from "./use-money-format";

export function BillingSection({
  subscriptions,
  t,
  portalLoading,
  cancelLoading,
  onManageBilling,
  onCancelClick,
}: {
  subscriptions: GetSubscriptionStatusQuery["subscriptionStatus"]["subscriptions"];
  t: (key: string) => string;
  portalLoading: boolean;
  cancelLoading: boolean;
  onManageBilling: (clientId: string) => void;
  onCancelClick: (target: CancelTarget) => void;
}) {
  const formatMoney = useMoneyFormat();
  const formatDate = useBillingDateFormat();
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-foreground">
        {t("userSettings.billing")}
      </h3>
      {subscriptions.map((subscription) => {
        const product =
          subscription.items[0]?.product?.name || t("userSettings.unknownPlan");
        const price = subscription.items[0]?.price;
        const amount = `${formatMoney(price?.amount ?? 0, price?.currency)}${t(
          price?.interval === "year"
            ? "userSettings.perYear"
            : "userSettings.perMonth",
        )}`;
        const endDate = subscription.currentPeriodEnd
          ? formatDate(subscription.currentPeriodEnd)
          : "";
        const isCanceled =
          isPendingCancellation(subscription) || !!subscription.canceledAt;

        const statusVariant =
          subscription.status === "active"
            ? "outline"
            : subscription.status === "past_due" ||
                subscription.status === "unpaid"
              ? "secondary"
              : "destructive";
        const statusClass =
          subscription.status === "active"
            ? "border-green-500 text-green-700 dark:text-green-400"
            : subscription.status === "past_due" ||
                subscription.status === "unpaid"
              ? "border-yellow-500 text-yellow-700 dark:text-yellow-400"
              : "";

        return (
          <div key={subscription.id} className="space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1 flex-1">
                <p className="text-sm font-medium flex items-center gap-2">
                  <Crown className="h-4 w-4 text-yellow-500" />
                  {product}
                </p>
                <p className="text-sm text-muted-foreground">{amount}</p>
                <Badge
                  variant={statusVariant}
                  className={`text-xs capitalize ${statusClass}`}
                >
                  {subscription.status}
                </Badge>
              </div>
              <div className="flex flex-col gap-2 shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onManageBilling(subscription.clientId)}
                  disabled={portalLoading}
                >
                  {portalLoading
                    ? t("userSettings.opening")
                    : t("userSettings.manageBilling")}
                </Button>
                {!isCanceled && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() =>
                      onCancelClick({
                        id: subscription.id,
                        clientId: subscription.clientId,
                        endsAt: subscription.currentPeriodEnd,
                      })
                    }
                    disabled={cancelLoading}
                  >
                    {t("userSettings.cancelSubscription")}
                  </Button>
                )}
              </div>
            </div>
            {/* A pending cancellation is shown, with Resume, in the
                Scheduled panel. */}
            {!isCanceled && subscription.currentPeriodEnd && (
              <p className="text-xs text-muted-foreground">
                {t("userSettings.renewsOn")} <strong>{endDate}</strong>
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
