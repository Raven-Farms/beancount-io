import { useEffect, useState } from "react";
import { ArrowUp, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/common/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/common/components/ui/dialog";
import type { UserTier } from "@/common/hooks/use-user-limits";
import { useErrorMessage } from "@/common/lib/errors/error-message";
import { featuresGained } from "@/common/lib/subscription/plan-features";
import type { TierQuota } from "@/common/hooks/use-all-tier-quotas";
import {
  useChangePlan,
  usePreviewPlanChange,
} from "@/features/user-settings/hooks/use-plan-change";
import {
  PlanChangeEffect,
  PlanChangeRefusal,
  type PreviewPlanChangeQuery,
} from "@/graphql/definitions";
import {
  cyclePrice,
  stripePlanConfig,
  type BillingCycle,
  type SubscriptionTier,
} from "./stripe-config";
import { useBillingDateFormat, useMoneyFormat } from "./use-money-format";
import { useQuotaNumberFormat } from "./use-quota-number-format";

type Translate = (
  key: string,
  params?: Record<string, string | number>,
) => string;
type Preview = PreviewPlanChangeQuery["previewPlanChange"];

export interface PlanChangeTarget {
  tier: SubscriptionTier;
  cycle: BillingCycle;
}

const TIER_LABEL_KEYS: Record<SubscriptionTier, string> = {
  premium: "aiAgent.premiumTier",
  growth: "aiAgent.growthTier",
  organization: "aiAgent.organizationTier",
};
const USER_TIERS: Record<SubscriptionTier, UserTier> = {
  premium: "PREMIUM",
  growth: "GROWTH",
  organization: "ORGANIZATION",
};
const REFUSAL_KEYS: Record<PlanChangeRefusal, string> = {
  [PlanChangeRefusal.CurrentPlan]: "userSettings.planChangeRefusalCurrent",
  [PlanChangeRefusal.SameTierAndCycle]:
    "userSettings.planChangeRefusalSameTier",
  [PlanChangeRefusal.MultipleSubscriptions]:
    "userSettings.planChangeRefusalMultiple",
  [PlanChangeRefusal.NoSubscription]:
    "userSettings.planChangeRefusalNoSubscription",
  [PlanChangeRefusal.ScheduledChange]: "userSettings.renewalChangesComingSoon",
};

type Outcome =
  | { type: "action"; hostedInvoiceUrl: string | null }
  | { type: "failed" }
  | { type: "refused"; refusal: PlanChangeRefusal | null };

/**
 * The confirm step for every immediate plan change and every checkout from
 * Billing (PRFAQ005 question 15). It shows what the server previewed — the
 * charge today, the credit, the next charge, the card and what the plan adds —
 * and confirms at the previewed proration time, so the charge equals the
 * preview. A payment the bank must approve goes to Stripe's hosted invoice
 * page; nothing here reports a pending change as done.
 */
export function PlanChangeSheet({
  target,
  currentTier,
  currentPlanLabel,
  quotaByUserTier,
  t,
  onClose,
  onCheckout,
  onManageBilling,
  onChanged,
  returnTo,
}: {
  target: PlanChangeTarget | null;
  /** A safe path back to where the prompt was, offered once the change lands. */
  returnTo?: string;
  currentTier: UserTier;
  currentPlanLabel: string;
  quotaByUserTier: Record<string, TierQuota>;
  t: Translate;
  onClose: () => void;
  onCheckout: (target: PlanChangeTarget) => void;
  onManageBilling: () => void;
  onChanged: () => void;
}) {
  const [runPreview, { data, loading, error }] = usePreviewPlanChange();
  const [changePlan, { loading: changing }] = useChangePlan();
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const formatError = useErrorMessage();
  const formatMoney = useMoneyFormat();
  const formatDate = useBillingDateFormat();
  const formatCount = useQuotaNumberFormat();

  const targetPriceId = target
    ? cyclePrice(target.tier, target.cycle).priceId
    : null;
  // The parent remounts the sheet per target (`key`), so state starts fresh.
  useEffect(() => {
    if (!targetPriceId) return;
    void runPreview({
      variables: {
        clientId: stripePlanConfig.clientId,
        priceId: targetPriceId,
      },
    });
  }, [targetPriceId, runPreview]);
  const preview = () => {
    if (!targetPriceId) return;
    setOutcome(null);
    void runPreview({
      variables: {
        clientId: stripePlanConfig.clientId,
        priceId: targetPriceId,
      },
    });
  };

  const planChange: Preview | undefined =
    data?.previewPlanChange.targetPriceId === targetPriceId
      ? data?.previewPlanChange
      : undefined;
  const targetLabel = target
    ? `${t(TIER_LABEL_KEYS[target.tier])} · ${t(
        target.cycle === "yearly"
          ? "userSettings.yearly"
          : "userSettings.monthly",
      )}`
    : "";

  const confirm = async () => {
    if (!target || !planChange) return;
    if (planChange.kind === "NEW") {
      onCheckout(target);
      return;
    }
    try {
      const response = await changePlan({
        variables: {
          clientId: stripePlanConfig.clientId,
          priceId: planChange.targetPriceId,
          prorationDate: planChange.prorationDate,
        },
      });
      const result = response.data?.changePlan;
      if (result?.status === "ACTIVE") {
        toast.success(
          t("userSettings.subscriptionUpgraded"),
          returnTo
            ? {
                action: {
                  label: t("userSettings.backToWork"),
                  // A full load, so every query reads the new plan's limits.
                  onClick: () => window.location.assign(returnTo),
                },
              }
            : undefined,
        );
        onChanged();
        onClose();
      } else if (result?.status === "REQUIRES_ACTION") {
        setOutcome({
          type: "action",
          hostedInvoiceUrl: result.hostedInvoiceUrl ?? null,
        });
      } else if (result?.status === "REFUSED") {
        setOutcome({ type: "refused", refusal: result.refusal ?? null });
      } else {
        setOutcome({ type: "failed" });
      }
    } catch (changeError) {
      toast.error(formatError(changeError));
    }
  };

  // Nothing can wait for the renewal date until those changes are scheduled,
  // so a scheduled preview is shown like a refusal.
  const refusal =
    outcome?.type === "refused"
      ? (outcome.refusal ?? PlanChangeRefusal.CurrentPlan)
      : (planChange?.refusal ??
        (planChange?.effect === PlanChangeEffect.Scheduled
          ? PlanChangeRefusal.ScheduledChange
          : null));

  const gained = target
    ? gainedLines(
        quotaByUserTier[currentTier],
        quotaByUserTier[USER_TIERS[target.tier]],
        t,
        formatCount,
      ).concat(
        featuresGained(currentTier, USER_TIERS[target.tier]).map((key) =>
          t(key),
        ),
      )
    : [];

  if (!target) return null;

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent data-testid="plan-change-sheet">
        <DialogHeader>
          <DialogTitle>
            {t("userSettings.planChangeTitle", { plan: targetLabel })}
          </DialogTitle>
          <DialogDescription>
            {currentPlanLabel} → {targetLabel}
          </DialogDescription>
        </DialogHeader>

        {loading || (!planChange && !error) ? (
          <p role="status" className="flex items-center gap-2 text-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t("userSettings.planChangePreviewing")}
          </p>
        ) : error || !planChange ? (
          <div className="space-y-3">
            <p className="text-sm">
              {t("userSettings.planChangePreviewFailed")}
            </p>
            <Button size="sm" variant="outline" onClick={preview}>
              {t("common.tryAgain")}
            </Button>
          </div>
        ) : outcome?.type === "action" ? (
          <div className="space-y-3" data-testid="plan-change-action">
            <p className="text-sm">
              {t("userSettings.planChangeRequiresAction")}
            </p>
            <DialogFooter>
              {outcome.hostedInvoiceUrl && (
                <Button asChild>
                  <a
                    href={outcome.hostedInvoiceUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t("userSettings.planChangeApprovePayment")}
                  </a>
                </Button>
              )}
              <Button variant="outline" onClick={onChanged}>
                {t("userSettings.refresh")}
              </Button>
            </DialogFooter>
          </div>
        ) : outcome?.type === "failed" ? (
          <div className="space-y-3" data-testid="plan-change-failed">
            <p className="text-sm">{t("userSettings.planChangeFailed")}</p>
            <DialogFooter>
              <Button onClick={preview}>{t("common.tryAgain")}</Button>
              <Button variant="outline" onClick={onManageBilling}>
                {t("userSettings.planChangeUseAnotherCard")}
              </Button>
            </DialogFooter>
          </div>
        ) : refusal ? (
          <div className="space-y-3">
            <p className="text-sm">{t(REFUSAL_KEYS[refusal])}</p>
            <DialogFooter>
              <Button variant="outline" onClick={onClose}>
                {t("userSettings.planChangeNotNow")}
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm">{t("userSettings.planChangeStartsToday")}</p>
            <div className="rounded-md border p-3">
              <div className="flex items-baseline justify-between text-sm font-semibold">
                <span>{t("userSettings.planChangeDueToday")}</span>
                <span data-testid="plan-change-due">
                  {formatMoney(planChange.amountDueToday, planChange.currency)}
                </span>
              </div>
              {planChange.creditApplied > 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {t("userSettings.planChangeCredit", {
                    credit: formatMoney(
                      planChange.creditApplied,
                      planChange.currency,
                    ),
                  })}
                </p>
              )}
              {planChange.nextChargeAt && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {t("userSettings.planChangeNext", {
                    amount: `${formatMoney(planChange.nextAmount, planChange.currency)}${t(
                      target?.cycle === "yearly"
                        ? "userSettings.perYear"
                        : "userSettings.perMonth",
                    )}`,
                    date: formatDate(planChange.nextChargeAt),
                  })}
                </p>
              )}
              {planChange.paymentMethod && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {t("userSettings.planChangeChargedTo", {
                    card: `${planChange.paymentMethod.brand} •••• ${planChange.paymentMethod.last4}`,
                  })}
                </p>
              )}
            </div>
            {gained.length > 0 && (
              <div>
                <p className="text-xs font-semibold">
                  {t("userSettings.planChangeWhatYouGet")}
                </p>
                <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                  {gained.map((line) => (
                    <li key={line} className="flex items-center gap-1.5">
                      <ArrowUp className="h-3 w-3 text-primary" />
                      {line}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <DialogFooter className="flex-col gap-2 sm:flex-row">
              <Button disabled={changing} onClick={() => void confirm()}>
                {planChange.kind === "NEW"
                  ? t("userSettings.planChangeContinueToCheckout")
                  : t("userSettings.planChangePayAndSwitch", {
                      amount: formatMoney(
                        planChange.amountDueToday,
                        planChange.currency,
                      ),
                    })}
              </Button>
              <Button variant="outline" onClick={onClose}>
                {t("userSettings.planChangeNotNow")}
              </Button>
            </DialogFooter>
            {planChange.kind !== "NEW" && (
              <p className="text-[11px] text-muted-foreground">
                {t("userSettings.planChangeCreditNote")}
              </p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

/** The quota lines that grow from the current plan to the target plan. */
function gainedLines(
  from: TierQuota | undefined,
  to: TierQuota | undefined,
  t: Translate,
  formatCount: (value: number) => string,
): string[] {
  if (!to) return [];
  const grows = (before: number | undefined, after: number) =>
    after === -1 ? before !== -1 : before !== undefined && after > before;
  const lines: string[] = [];
  if (grows(from?.maxLedgers, to.maxLedgers)) {
    lines.push(
      to.maxLedgers === -1
        ? t("userSettings.unlimitedLedgers")
        : t("userSettings.includedLedgers", {
            count: to.maxLedgers,
            formattedCount: formatCount(to.maxLedgers),
          }),
    );
  }
  if (grows(from?.maxCollaboratorsPerLedger, to.maxCollaboratorsPerLedger)) {
    lines.push(
      to.maxCollaboratorsPerLedger === -1
        ? t("userSettings.unlimitedCollaborators")
        : t("userSettings.collaboratorsPerLedger", {
            count: to.maxCollaboratorsPerLedger,
            formattedCount: formatCount(to.maxCollaboratorsPerLedger),
          }),
    );
  }
  if (grows(from?.aiCfoTokensMax, to.aiCfoTokensMax)) {
    lines.push(
      t("userSettings.aiTokensPerMonth", {
        count: formatCount(to.aiCfoTokensMax),
      }),
    );
  }
  return lines;
}
