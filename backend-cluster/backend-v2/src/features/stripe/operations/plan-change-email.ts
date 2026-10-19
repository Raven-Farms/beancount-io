import type Stripe from "stripe";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import type { ISendGrid } from "@/foundation/sendgrid";
import {
  planChangeEmailSubject,
  renderPlanChangeHtml,
  renderPlanChangeText,
  type PlanChangeEmailParams,
} from "@/shared/email-templates";
import {
  SUBSCRIPTION_CONFIG,
  TIER_DISPLAY_NAMES,
  type PlanConfig,
  type TierLimits,
} from "../service/stripe";
import { limitChanges } from "./plan-change-preview";
import {
  pendingChange,
  type ScheduledChangeNotice,
} from "./plan-change-schedule";

export interface PlanChangeEmailDeps {
  models: Pick<IModels, "user" | "sentBillingEmail">;
  db: DbExecutor;
  sendgrid: ISendGrid;
}

export type PlanChangeEmailKind = PlanChangeEmailParams["kind"];
export type PlanChangeEmailOutcome =
  | "sent"
  | "already-sent"
  | "nothing-scheduled"
  | "no-recipient";

const LIMIT_LABELS: Record<keyof TierLimits, string> = {
  maxLedgers: "Ledgers",
  maxCollaboratorsPerLedger: "Collaborators per ledger",
  aiCfoTokensMax: "AI Assistant tokens per month",
  maxDirectives: "Ledger entries",
};

function planName(plan: PlanConfig): string {
  return `${TIER_DISPLAY_NAMES[plan.tier]} · ${plan.interval === "year" ? "Yearly" : "Monthly"}`;
}

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
  const item = subscription.items.data.find((each) =>
    plans.some((plan) => plan.priceId === each.price.id),
  );
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
  deps: PlanChangeEmailDeps,
  kind: PlanChangeEmailKind,
  userId: string,
  clientId: string,
  notice: ScheduledChangeNotice,
): Promise<PlanChangeEmailOutcome> {
  const { plans, portalReturnUrl } = SUBSCRIPTION_CONFIG[clientId];
  const current = plans.find((plan) => plan.priceId === notice.currentPriceId);
  const target = plans.find((plan) => plan.priceId === notice.change.priceId);
  if (!current || !target) return "nothing-scheduled";
  const user = await deps.models.user.getById(deps.db, userId);
  if (!user?.email) return "no-recipient";

  const params: PlanChangeEmailParams = {
    kind,
    currentPlan: planName(current),
    newPlan: planName(target),
    effectiveDate: notice.change.effectiveAt.toLocaleDateString("en-US", {
      dateStyle: "long",
      timeZone: "UTC",
    }),
    limitChanges: limitChanges(current.tier, target.tier)
      .filter((line) => line.from !== line.to)
      .map((line) => ({
        label: LIMIT_LABELS[line.limit],
        from: limitValue(line.from),
        to: limitValue(line.to),
      })),
    billingUrl: portalReturnUrl,
  };
  // Rendered before claiming, so nothing that can throw sits between the
  // claim and the send.
  const mail = {
    to: user.email,
    subject: planChangeEmailSubject(params),
    html: renderPlanChangeHtml(params),
    text: renderPlanChangeText(params),
  };
  const key = emailKey(kind, notice);
  if (!(await deps.models.sentBillingEmail.claim(deps.db, key))) {
    return "already-sent";
  }
  try {
    await deps.sendgrid.sendMail(mail);
  } catch (error) {
    await deps.models.sentBillingEmail.release(deps.db, key);
    throw error;
  }
  return "sent";
}
