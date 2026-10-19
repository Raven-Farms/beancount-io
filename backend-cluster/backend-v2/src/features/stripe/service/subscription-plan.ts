import type Stripe from "stripe";
import {
  BILLING_CLIENT_ID,
  SUBSCRIPTION_CONFIG,
  SubscriptionTier,
  type PlanConfig,
} from "./stripe";

export type ClientSubscription = Stripe.Subscription & { clientId: string };

// Bump when period verification rules change; older cached values must be re-read.
// 2: a past-due subscription counts as paid, and the tier is stored with it.
export const SUBSCRIPTION_PERIOD_VERIFICATION_VERSION = 2;

/**
 * A billing binding whose cached period this version verified and that has
 * not ended yet. Both cached-tier paths use this one test, so a version bump
 * invalidates them together.
 */
export function holdsVerifiedPeriod(
  binding: {
    clientId: string;
    periodVerificationVersion?: number | null;
    currentPeriodEnd?: Date | null;
  },
  now = Date.now(),
): boolean {
  return (
    binding.clientId === BILLING_CLIENT_ID &&
    binding.periodVerificationVersion ===
      SUBSCRIPTION_PERIOD_VERIFICATION_VERSION &&
    !!binding.currentPeriodEnd &&
    binding.currentPeriodEnd.getTime() > now
  );
}

/**
 * When Stripe next retries a past-due renewal (unix seconds), read from the
 * expanded latest invoice; null once it has stopped retrying, or when the
 * invoice was not expanded.
 */
export function pastDueRetry(subscription: Stripe.Subscription): number | null {
  const invoice = subscription.latest_invoice;
  if (subscription.status !== "past_due" || !invoice) return null;
  if (typeof invoice === "string") return null;
  return invoice.status === "open" && invoice.next_payment_attempt
    ? invoice.next_payment_attempt
    : null;
}

/**
 * Whether a subscription holds its paid tier. A past-due one keeps its plan
 * only while Stripe still retries the renewal (PRFAQ005 question 21,
 * decision 1), so an account that leaves subscriptions past due after the
 * last retry does not keep a paid tier for ever.
 */
export function holdsPaidTier(subscription: Stripe.Subscription): boolean {
  if (!subscription.livemode) return false;
  if (subscription.status === "active") return true;
  return pastDueRetry(subscription) !== null;
}

/** The id of a Stripe field that is either an id or the expanded object. */
export function expandableId(value: string | { id: string }): string {
  return typeof value === "string" ? value : value.id;
}

export function customerId(customer: Stripe.Subscription["customer"]): string {
  return expandableId(customer);
}

/**
 * The subscription item billing one of `plans`, with that plan; undefined
 * when none is ours, as on the other products the Stripe account bills.
 */
export function planItem(
  subscription: Stripe.Subscription,
  plans: readonly PlanConfig[],
): { item: Stripe.SubscriptionItem; plan: PlanConfig } | undefined {
  for (const item of subscription.items.data) {
    const plan = plans.find((each) => each.priceId === item.price.id);
    if (plan) return { item, plan };
  }
  return undefined;
}

// The same recognized prices and paid-status policy drive tier and cache.
export function subscriptionTier(
  subscription: ClientSubscription,
): SubscriptionTier {
  if (!holdsPaidTier(subscription)) return SubscriptionTier.FREE;
  const plans = SUBSCRIPTION_CONFIG[subscription.clientId]?.plans ?? [];
  const tiers = subscription.items.data.flatMap((item) => {
    const plan = plans.find((plan) => plan.priceId === item.price.id);
    return plan ? [plan.tier] : [];
  });
  return highestTier(tiers);
}

const tierOrder = [
  SubscriptionTier.FREE,
  SubscriptionTier.PREMIUM,
  SubscriptionTier.GROWTH,
  SubscriptionTier.ORGANIZATION,
  SubscriptionTier.ENTERPRISE,
];

/** Position in the upgrade order: a higher rank is a higher tier. */
export function tierRank(tier: SubscriptionTier): number {
  return tierOrder.indexOf(tier);
}

export function highestTier(tiers: SubscriptionTier[]): SubscriptionTier {
  return tiers.reduce(
    (best, tier) => (tierRank(tier) > tierRank(best) ? tier : best),
    SubscriptionTier.FREE,
  );
}

export function subscriptionPeriodEnd(
  subscriptions: ClientSubscription[],
): Date | null {
  const ends = subscriptions.flatMap((subscription) => {
    if (subscriptionTier(subscription) === SubscriptionTier.FREE) return [];
    const plans = SUBSCRIPTION_CONFIG[subscription.clientId].plans;
    // A past-due period is not paid for: it is held only until the retry.
    const retry = pastDueRetry(subscription);
    return subscription.items.data
      .filter((item) => plans.some((plan) => plan.priceId === item.price.id))
      .map((item) =>
        retry === null
          ? item.current_period_end
          : Math.min(item.current_period_end, retry),
      )
      .filter((end) => Number.isFinite(end) && end > 0);
  });
  return ends.length ? new Date(Math.max(...ends) * 1000) : null;
}
