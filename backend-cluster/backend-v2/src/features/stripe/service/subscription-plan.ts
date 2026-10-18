import type Stripe from "stripe";
import { SUBSCRIPTION_CONFIG, SubscriptionTier } from "./stripe";

export type ClientSubscription = Stripe.Subscription & { clientId: string };

// Bump when period verification rules change; older cached values must be re-read.
export const SUBSCRIPTION_PERIOD_VERIFICATION_VERSION = 1;

export function customerId(customer: Stripe.Subscription["customer"]): string {
  return typeof customer === "string" ? customer : customer.id;
}

// The same recognized prices and active-status policy drive tier and cache.
export function subscriptionTier(
  subscription: ClientSubscription,
): SubscriptionTier {
  if (!subscription.livemode || subscription.status !== "active")
    return SubscriptionTier.FREE;
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

export function highestTier(tiers: SubscriptionTier[]): SubscriptionTier {
  return tiers.reduce(
    (best, tier) =>
      tierOrder.indexOf(tier) > tierOrder.indexOf(best) ? tier : best,
    SubscriptionTier.FREE,
  );
}

export function subscriptionPeriodEnd(
  subscriptions: ClientSubscription[],
): Date | null {
  const ends = subscriptions.flatMap((subscription) => {
    if (subscriptionTier(subscription) === SubscriptionTier.FREE) return [];
    const plans = SUBSCRIPTION_CONFIG[subscription.clientId].plans;
    return subscription.items.data
      .filter((item) => plans.some((plan) => plan.priceId === item.price.id))
      .map((item) => item.current_period_end)
      .filter((end) => Number.isFinite(end) && end > 0);
  });
  return ends.length ? new Date(Math.max(...ends) * 1000) : null;
}
