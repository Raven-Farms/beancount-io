import type Stripe from "stripe";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import { logger } from "@/shared/logger";
import {
  classifyPlanChange,
  PLAN_CHANGE_EFFECT,
  type PlanChangeEffect,
  type PlanChangeKind,
  type PlanChangeRefusal,
  resolveTargetPlan,
} from "../service/plan-change";
import {
  SubscriptionTier,
  TIER_LIMITS,
  type BillingInterval,
  type PlanConfig,
  type TierLimits,
} from "../service/stripe";
import { customerId } from "../service/subscription-plan";
import { loadActivePlans } from "./current-plan";

const previewLogger = logger.child({ module: "plan-change-preview" });

export interface PaymentMethodSummaryView {
  brand: string;
  last4: string;
}

interface PlanLimitChangeView {
  limit: keyof TierLimits;
  from: number;
  to: number;
}

/**
 * What choosing `targetPriceId` would do, computed before any change is made.
 * Amounts are in the currency's minor unit (cents), as Stripe reports them.
 */
export interface PlanChangePreviewView {
  kind: PlanChangeKind | null;
  refusal: PlanChangeRefusal | null;
  effect: PlanChangeEffect | null;
  currentPriceId: string | null;
  targetPriceId: string;
  currency: string;
  amountDueToday: number;
  creditApplied: number;
  nextAmount: number;
  nextChargeAt: Date | null;
  effectiveAt: Date | null;
  /** Unix seconds; `changePlan` must charge at this instant to match. */
  prorationDate: number | null;
  /** For `SPLIT`: the higher tier on the current cycle, to preview as "now". */
  alternativePriceId: string | null;
  limitChanges: PlanLimitChangeView[];
  paymentMethod: PaymentMethodSummaryView | null;
}

export interface PlanChangePreviewDeps {
  stripe: Stripe;
  models: Pick<IModels, "paidCustomer">;
  db: DbExecutor;
  now?: () => Date;
}

const LIMIT_KEYS: readonly (keyof TierLimits)[] = [
  "maxLedgers",
  "maxCollaboratorsPerLedger",
  "aiCfoTokensMax",
  "maxDirectives",
];

function limitChanges(
  from: SubscriptionTier,
  to: SubscriptionTier,
): PlanLimitChangeView[] {
  return LIMIT_KEYS.map((limit) => ({
    limit,
    from: TIER_LIMITS[from][limit],
    to: TIER_LIMITS[to][limit],
  }));
}

function addInterval(at: Date, interval: BillingInterval): Date {
  const next = new Date(at);
  if (interval === "year") next.setUTCFullYear(next.getUTCFullYear() + 1);
  else next.setUTCMonth(next.getUTCMonth() + 1);
  return next;
}

function cardOf(
  method: string | Stripe.PaymentMethod | null | undefined,
): PaymentMethodSummaryView | null {
  if (!method || typeof method === "string" || !method.card) return null;
  return { brand: method.card.brand, last4: method.card.last4 };
}

/**
 * The card a renewal or plan change would charge: the subscription's own
 * default, else the customer's invoice default. Returns null rather than
 * failing a preview when Stripe cannot say.
 */
export async function defaultCard(
  stripe: Stripe,
  subscription: Stripe.Subscription,
): Promise<PaymentMethodSummaryView | null> {
  try {
    const own = subscription.default_payment_method;
    if (own) {
      return typeof own === "string"
        ? cardOf(await stripe.paymentMethods.retrieve(own))
        : cardOf(own);
    }
    const customer = await stripe.customers.retrieve(
      customerId(subscription.customer),
      { expand: ["invoice_settings.default_payment_method"] },
    );
    if (customer.deleted) return null;
    return cardOf(customer.invoice_settings?.default_payment_method);
  } catch (error) {
    previewLogger.warn("Could not resolve the default payment method", {
      errorMessage: error instanceof Error ? error.message : String(error),
    });
    return null;
  }
}

function sameTierOnCycle(
  plans: PlanConfig[],
  tier: SubscriptionTier,
  interval: BillingInterval,
): string | null {
  return (
    plans.find(
      (plan) =>
        plan.tier === tier && plan.interval === interval && !plan.retired,
    )?.priceId ?? null
  );
}

async function listPrice(
  stripe: Stripe,
  priceId: string,
): Promise<{ amount: number; currency: string }> {
  const price = await stripe.prices.retrieve(priceId);
  return { amount: price.unit_amount ?? 0, currency: price.currency };
}

function base(
  targetPriceId: string,
  currency: string,
): Omit<PlanChangePreviewView, "kind" | "refusal" | "effect"> {
  return {
    currentPriceId: null,
    targetPriceId,
    currency,
    amountDueToday: 0,
    creditApplied: 0,
    nextAmount: 0,
    nextChargeAt: null,
    effectiveAt: null,
    prorationDate: null,
    alternativePriceId: null,
    limitChanges: [],
    paymentMethod: null,
  };
}

/**
 * Preview a plan change for one user against one billing client.
 *
 * Classification comes from configuration alone (`classifyPlanChange`); only
 * immediate changes ask Stripe what they would charge, at a fixed proration
 * time the caller hands back to `changePlan`.
 */
export async function previewPlanChange(
  deps: PlanChangePreviewDeps,
  userId: string,
  clientId: string,
  targetPriceId: string,
): Promise<PlanChangePreviewView> {
  const { plans, target } = resolveTargetPlan(clientId, targetPriceId);

  const { stripe } = deps;
  const now = deps.now?.() ?? new Date();
  const { active } = await loadActivePlans(
    stripe,
    deps.models,
    deps.db,
    userId,
    clientId,
    plans,
  );

  const { amount: targetAmount, currency } = await listPrice(
    stripe,
    targetPriceId,
  );

  if (active.length > 1) {
    // Two paid subscriptions on one customer is a duplicate purchase; never
    // guess which one a change should move.
    previewLogger.warn("Plan change refused: several active subscriptions", {
      count: active.length,
    });
    return {
      ...base(targetPriceId, currency),
      kind: null,
      refusal: "MULTIPLE_SUBSCRIPTIONS",
      effect: null,
    };
  }

  const current = active[0] ?? null;
  const classification = classifyPlanChange(current?.plan ?? null, target);
  const fromTier = current?.plan.tier ?? SubscriptionTier.FREE;
  const shared = {
    ...base(targetPriceId, currency),
    currentPriceId: current?.plan.priceId ?? null,
    nextAmount: targetAmount,
    limitChanges: limitChanges(fromTier, target.tier),
  };

  if ("refusal" in classification) {
    return {
      ...shared,
      kind: null,
      refusal: classification.refusal,
      effect: null,
    };
  }

  const { kind } = classification;
  const effect = PLAN_CHANGE_EFFECT[kind];

  if (!current) {
    return {
      ...shared,
      kind,
      refusal: null,
      effect,
      amountDueToday: targetAmount,
      effectiveAt: now,
      nextChargeAt: addInterval(now, target.interval),
    };
  }

  const periodEnd = new Date(current.item.current_period_end * 1000);
  const paymentMethod = await defaultCard(stripe, current.subscription);

  if (effect === "SCHEDULED") {
    return {
      ...shared,
      kind,
      refusal: null,
      effect,
      effectiveAt: periodEnd,
      nextChargeAt: periodEnd,
      paymentMethod,
      alternativePriceId:
        kind === "SPLIT"
          ? sameTierOnCycle(plans, target.tier, current.plan.interval)
          : null,
    };
  }

  const prorationDate = Math.floor(now.getTime() / 1000);
  const invoice = await stripe.invoices.createPreview({
    customer: customerId(current.subscription.customer),
    subscription: current.subscription.id,
    subscription_details: {
      items: [{ id: current.item.id, price: targetPriceId }],
      proration_behavior: "always_invoice",
      proration_date: prorationDate,
    },
  });
  const creditApplied = invoice.lines.data
    .filter((line) => line.amount < 0)
    .reduce((total, line) => total - line.amount, 0);
  const cycleChanges = current.plan.interval !== target.interval;

  return {
    ...shared,
    kind,
    refusal: null,
    effect,
    currency: invoice.currency,
    amountDueToday: invoice.amount_due,
    creditApplied,
    effectiveAt: now,
    prorationDate,
    // A new billing cycle starts now; otherwise the renewal date holds.
    nextChargeAt: cycleChanges ? addInterval(now, target.interval) : periodEnd,
    paymentMethod,
  };
}

