import type Stripe from "stripe";
import {
  planChangeEmailSubject,
  renderPlanChangeHtml,
  renderPlanChangeText,
  type PlanChangeEmailParams,
} from "@/shared/email-templates";
import {
  SUBSCRIPTION_CONFIG,
  type PlanConfig,
  type TierLimits,
} from "../service/stripe";
import { planItem } from "../service/subscription-plan";
import {
  longDate,
  planName,
  sendBillingEmailOnce,
  type BillingEmailDeps,
  type BillingEmailOutcome,
} from "./billing-email";
import { limitChanges } from "./plan-change-preview";
import {
  pendingChange,
  type ScheduledChangeNotice,
} from "./plan-change-schedule";

export type PlanChangeEmailKind = PlanChangeEmailParams["kind"];

const LIMIT_LABELS: Record<keyof TierLimits, string> = {
  maxLedgers: "Ledgers",
  maxCollaboratorsPerLedger: "Collaborators per ledger",
  aiCfoTokensMax: "AI Assistant tokens per month",
  maxDirectives: "Ledger entries",
};

function limitValue(value: number): string {
  return value === -1 ? "Unlimited" : value.toLocaleString("en-US");
}

/**
 * Names what an email announced, so each is sent once. A confirmation also
 * names the change it replaced: scheduling A, then B, then A again
 * announces all three, while confirming A twice announces it once.
 */
function emailKey(kind: PlanChangeEmailKind, notice: ScheduledChangeNotice) {
  const at = (change: { priceId: string; effectiveAt: Date }) =>
    `${change.priceId}@${change.effectiveAt.toISOString()}`;
  const replaced =
    kind === "scheduled"
      ? `${notice.previous ? at(notice.previous) : "none"}>`
      : "";
  return `plan-change-${kind}:${notice.scheduleId}:${replaced}${at(notice.change)}`;
}

/**
 * The change a subscription's schedule makes at its coming renewal, read
 * with the schedule expanded, or null. A change set for a later renewal is
 * not this renewal's news.
 */
export function changeAtRenewal(
  subscription: Stripe.Subscription,
  plans: readonly PlanConfig[],
): ScheduledChangeNotice | null {
  const change = pendingChange(subscription, plans);
  const item = planItem(subscription, plans)?.item;
  const schedule = subscription.schedule;
  if (!change || !item || !schedule || typeof schedule === "string") {
    return null;
  }
  if (change.effectiveAt.getTime() !== item.current_period_end * 1000) {
    return null;
  }
  return {
    subscriptionId: subscription.id,
    scheduleId: schedule.id,
    currentPriceId: item.price.id,
    change,
  };
}

/**
 * Email the subscriber about a scheduled plan change (PRFAQ005 question 17):
 * a confirmation once it is scheduled, a reminder before it lands. Each is
 * sent once (see `emailKey`); a failed send gives the claim back and
 * rethrows, so a retry can send it.
 */
export async function emailScheduledChange(
  deps: BillingEmailDeps,
  kind: PlanChangeEmailKind,
  userId: string,
  clientId: string,
  notice: ScheduledChangeNotice,
): Promise<BillingEmailOutcome> {
  const { plans, portalReturnUrl } = SUBSCRIPTION_CONFIG[clientId];
  const current = plans.find((plan) => plan.priceId === notice.currentPriceId);
  const target = plans.find((plan) => plan.priceId === notice.change.priceId);
  if (!current || !target) return "not-applicable";

  const params: PlanChangeEmailParams = {
    kind,
    currentPlan: planName(current),
    newPlan: planName(target),
    effectiveDate: longDate(notice.change.effectiveAt),
    limitChanges: limitChanges(current.tier, target.tier)
      .filter((line) => line.from !== line.to)
      .map((line) => ({
        label: LIMIT_LABELS[line.limit],
        from: limitValue(line.from),
        to: limitValue(line.to),
      })),
    billingUrl: portalReturnUrl,
  };
  return sendBillingEmailOnce(deps, userId, emailKey(kind, notice), {
    subject: planChangeEmailSubject(params),
    html: renderPlanChangeHtml(params),
    text: renderPlanChangeText(params),
  });
}
