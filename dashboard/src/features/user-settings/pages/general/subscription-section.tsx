import { useMemo, useState } from "react";
import { CreditCard, Loader2, AlertCircle } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/common/components/ui/card";
import { Separator } from "@/common/components/ui/separator";
import { toast } from "sonner";
import { useTranslations } from "@/common/hooks/use-translations";
import { useErrorMessage } from "@/common/lib/errors/error-message";
import { useUserLimits } from "@/common/hooks/use-user-limits";
import { useAiCfoUsage } from "@/common/hooks/use-ai-cfo-usage";
import { useCreateSubscriptionSession } from "@/features/user-settings/hooks/use-create-subscription-session";
import { useSubscriptionStatus } from "@/features/user-settings/hooks/use-subscription-status";
import { useSubscriptionPortal } from "@/features/user-settings/hooks/use-subscription-portal";
import { useSubscriptionCancel } from "@/features/user-settings/hooks/use-subscription-cancel";
import { useSubscriptionResume } from "@/features/user-settings/hooks/use-subscription-resume";
import {
  cyclePrice,
  LEGACY_PRICE_IDS,
  stripePlanConfig,
  type BillingCycle,
  type SubscriptionTier,
} from "./stripe-config";
import {
  getTierInfo,
  getUpgradeTiers,
} from "@/common/lib/subscription/tier-config";
import {
  useAllTierQuotas,
  type TierQuota,
} from "@/common/hooks/use-all-tier-quotas";
import { CurrentPlanBanner } from "./subscription-plan-banner";
import { describeTierQuota } from "./tier-quota-summary";
import { CheckoutConfirmation } from "./checkout-confirmation";
import { useCheckoutConfirmation } from "./use-checkout-confirmation";
import { useMoneyFormat } from "./use-money-format";
import { useQuotaNumberFormat } from "./use-quota-number-format";
import {
  rememberReturnPath,
  takeReturnPath,
} from "@/features/user-settings/lib/billing-return";
import { UsageOverview } from "./subscription-usage-overview";
import { PlanPicker } from "./subscription-plan-picker";
import { PayYearlyOffer } from "./subscription-pay-yearly";
import { PlanChangeSheet, type PlanChangeTarget } from "./plan-change-sheet";
import { track } from "@/common/analytics";
import type { PlanInterval } from "@/common/lib/subscription/plan-change";
import type { UserTier } from "@/common/hooks/use-user-limits";
import { BillingSection } from "./subscription-billing-section";
import {
  CancelSubscriptionDialog,
  ResumeSubscriptionDialog,
} from "./subscription-dialogs";

const TIER_KEYS: Partial<Record<UserTier, SubscriptionTier>> = {
  PREMIUM: "premium",
  GROWTH: "growth",
  ORGANIZATION: "organization",
};
const USER_TIERS: Record<SubscriptionTier, UserTier> = {
  premium: "PREMIUM",
  growth: "GROWTH",
  organization: "ORGANIZATION",
};

function SubscriptionSkeleton() {
  return (
    <div className="flex items-center justify-center py-8">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  );
}

function SubscriptionError({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-8">
      <div className="text-center">
        <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}

function SubscriptionHeader({ t }: { t: (key: string) => string }) {
  return (
    <CardHeader>
      <div className="flex items-center gap-2">
        <CreditCard className="h-5 w-5" />
        <CardTitle>
          <h2>{t("userSettings.subscription")}</h2>
        </CardTitle>
      </div>
      <CardDescription>{t("userSettings.manageSubscription")}</CardDescription>
    </CardHeader>
  );
}

export function SubscriptionSection({
  checkoutReturned = false,
  returnTo,
  onCheckoutDismiss,
}: {
  /** Stripe Checkout just returned here with `checkout=success`. */
  checkoutReturned?: boolean;
  /** Where the purchase began, to offer the way back after Checkout. */
  returnTo?: string;
  onCheckoutDismiss?: () => void;
} = {}) {
  const { t } = useTranslations();
  const formatError = useErrorMessage();
  const {
    tier,
    limits,
    isLoading: limitsLoading,
    refetch: refetchUserLimits,
  } = useUserLimits();
  const {
    aiCfoTokensUsed,
    aiCfoTokensMax,
    isLoading: aiCfoLoading,
  } = useAiCfoUsage();
  const { quotas: tierQuotas, isLoading: quotasLoading } = useAllTierQuotas();

  const {
    loading: subscriptionLoading,
    error: subscriptionError,
    refetch: refetchSubscription,
    hasActiveStripeSubscription,
    renewalDate,
    subscriptions,
  } = useSubscriptionStatus();

  const { handleManageBilling, loading: portalLoading } =
    useSubscriptionPortal();
  const {
    loading: cancelLoading,
    showCancelDialog,
    setShowCancelDialog,
    selectedSubscription,
    handleCancelClick,
    handleCancelConfirm,
  } = useSubscriptionCancel();
  const {
    loading: resumeLoading,
    showResumeDialog,
    setShowResumeDialog,
    selectedResumeSubscription,
    handleResumeClick,
    handleResumeConfirm,
  } = useSubscriptionResume();

  const { createSubscriptionSession, loading: checkoutLoading } =
    useCreateSubscriptionSession();
  const [sheetTarget, setSheetTarget] = useState<PlanChangeTarget | null>(null);

  const stripeConfig = stripePlanConfig;

  const upgradeTiers = useMemo(() => getUpgradeTiers(tier), [tier]);

  const quotaByUserTier = useMemo(() => {
    const map: Record<string, TierQuota> = {};
    for (const q of tierQuotas ?? []) {
      map[q.tier] = q;
    }
    return map;
  }, [tierQuotas]);

  const handleUpgradeCheckout = async (
    tierKey: SubscriptionTier,
    cycle: BillingCycle,
  ) => {
    try {
      const response = await createSubscriptionSession({
        variables: {
          clientId: stripeConfig.clientId,
          priceId: cyclePrice(tierKey, cycle).priceId,
        },
      });
      const result = response.data?.createSubscriptionSession;
      if (result?.success && result.sessionUrl) {
        rememberReturnPath(returnTo);
        window.location.href = result.sessionUrl;
      } else {
        toast.error(
          result?.message || t("userSettings.failedToCreateCheckoutSession"),
        );
      }
    } catch (error) {
      toast.error(formatError(error));
    }
  };

  const currentSubscription = hasActiveStripeSubscription
    ? subscriptions?.[0]
    : undefined;
  const currentPrice = currentSubscription?.items[0]?.price;
  const currentInterval: PlanInterval | null =
    currentPrice?.interval === "year"
      ? "year"
      : currentPrice?.interval === "month"
        ? "month"
        : null;
  const currentTierKey = TIER_KEYS[tier] ?? null;

  // Every immediate choice confirms in the sheet, which previews the charge.
  const handleChoose = (tierKey: SubscriptionTier, cycle: BillingCycle) =>
    setSheetTarget({ tier: tierKey, cycle });

  const startCheckout = (target: PlanChangeTarget) => {
    track("checkout_started", {
      surface: "settings_billing",
      target_tier: USER_TIERS[target.tier],
    });
    return handleUpgradeCheckout(target.tier, target.cycle);
  };

  const isLoading =
    limitsLoading || subscriptionLoading || aiCfoLoading || quotasLoading;

  const formatMoney = useMoneyFormat();
  const formatCount = useQuotaNumberFormat();
  const [checkoutReturnPath] = useState(() =>
    checkoutReturned ? takeReturnPath() : null,
  );
  const confirmation = useCheckoutConfirmation(
    checkoutReturned,
    hasActiveStripeSubscription,
    () => {
      void refetchSubscription();
      void refetchUserLimits();
    },
  );
  const tierInfo = getTierInfo(tier);
  const planLabel = [
    tierInfo ? t(tierInfo.labelKey) : t("userSettings.freePlan"),
    currentInterval
      ? t(
          currentInterval === "year"
            ? "userSettings.yearly"
            : "userSettings.monthly",
        )
      : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const aiPercentage =
    aiCfoTokensMax > 0
      ? Math.min((aiCfoTokensUsed / aiCfoTokensMax) * 100, 100)
      : 0;
  const ledgerPercentage =
    limits && limits.ledgersMax > 0
      ? Math.min((limits.ledgersUsed / limits.ledgersMax) * 100, 100)
      : 0;
  const showUpgradeNudge =
    upgradeTiers.length > 0 && (aiPercentage >= 80 || ledgerPercentage >= 100);

  return (
    <Card>
      <SubscriptionHeader t={t} />
      <CardContent className="space-y-6">
        {checkoutReturned && (
          <CheckoutConfirmation
            state={confirmation}
            planLabel={planLabel}
            renewal={
              renewalDate && currentPrice
                ? {
                    date: renewalDate,
                    amount: formatMoney(
                      currentPrice.amount,
                      currentPrice.currency,
                    ),
                  }
                : null
            }
            unlocked={
              quotaByUserTier[tier]
                ? describeTierQuota(quotaByUserTier[tier], t, formatCount)
                : null
            }
            returnTo={checkoutReturnPath}
            t={t}
            onRefresh={() => {
              void refetchSubscription();
              void refetchUserLimits();
            }}
            onDismiss={() => onCheckoutDismiss?.()}
          />
        )}
        {isLoading ? (
          <SubscriptionSkeleton />
        ) : subscriptionError ? (
          <SubscriptionError
            message={t("userSettings.failedToLoadSubscription")}
          />
        ) : (
          <>
            <CurrentPlanBanner
              tier={tier}
              renewalDate={renewalDate}
              tierQuota={quotaByUserTier[tier] ?? null}
              t={t}
              billing={
                currentPrice
                  ? {
                      interval: currentInterval,
                      amount: currentPrice.amount,
                      currency: currentPrice.currency,
                      isLegacyPrice: LEGACY_PRICE_IDS.has(currentPrice.id),
                      paymentMethod: currentSubscription?.paymentMethod ?? null,
                    }
                  : null
              }
            />

            {currentInterval === "month" && currentTierKey && (
              <PayYearlyOffer
                tier={currentTierKey}
                t={t}
                busy={checkoutLoading}
                onSwitch={() =>
                  setSheetTarget({ tier: currentTierKey, cycle: "yearly" })
                }
              />
            )}

            {limits && (
              <>
                <Separator />
                <UsageOverview
                  limits={limits}
                  aiCfoTokensUsed={aiCfoTokensUsed}
                  aiCfoTokensMax={aiCfoTokensMax}
                  t={t}
                />
              </>
            )}

            <Separator />
            {showUpgradeNudge && (
              <div className="flex items-start gap-2 p-3 rounded-md bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-800 text-xs text-yellow-800 dark:text-yellow-200">
                <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0 text-yellow-600 dark:text-yellow-400" />
                <span>
                  {ledgerPercentage >= 100
                    ? t("page.dashboard.ledgerLimitReached")
                    : t("userSettings.aiUsageUpgradeNudge", {
                        percentage: Math.round(aiPercentage),
                      })}
                </span>
              </div>
            )}
            <PlanPicker
              tier={tier}
              currentInterval={currentInterval}
              quotaByUserTier={quotaByUserTier}
              t={t}
              busy={checkoutLoading}
              onChoose={handleChoose}
            />

            {hasActiveStripeSubscription && subscriptions && (
              <>
                <Separator />
                <BillingSection
                  subscriptions={subscriptions}
                  t={t}
                  portalLoading={portalLoading}
                  cancelLoading={cancelLoading}
                  resumeLoading={resumeLoading}
                  onManageBilling={handleManageBilling}
                  onCancelClick={handleCancelClick}
                  onResumeClick={handleResumeClick}
                />
              </>
            )}
          </>
        )}
      </CardContent>

      <PlanChangeSheet
        key={sheetTarget ? `${sheetTarget.tier}-${sheetTarget.cycle}` : "none"}
        target={sheetTarget}
        currentTier={tier}
        currentPlanLabel={planLabel}
        quotaByUserTier={quotaByUserTier}
        t={t}
        onClose={() => setSheetTarget(null)}
        onCheckout={(target) => void startCheckout(target)}
        onManageBilling={() => void handleManageBilling(stripeConfig.clientId)}
        onChanged={() => {
          void refetchSubscription();
          void refetchUserLimits();
        }}
      />

      <CancelSubscriptionDialog
        open={showCancelDialog}
        onOpenChange={setShowCancelDialog}
        selectedSubscription={selectedSubscription}
        cancelLoading={cancelLoading}
        t={t}
        onConfirm={handleCancelConfirm}
      />

      <ResumeSubscriptionDialog
        open={showResumeDialog}
        onOpenChange={setShowResumeDialog}
        selectedSubscription={selectedResumeSubscription}
        resumeLoading={resumeLoading}
        t={t}
        onConfirm={handleResumeConfirm}
      />
    </Card>
  );
}
