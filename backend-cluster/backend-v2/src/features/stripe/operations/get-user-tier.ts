import { logger } from "@/shared/logger";
import { SubscriptionTier, TierLimits, getTierLimits } from "../service/stripe";
import { highestTier, subscriptionTier } from "../service/subscription-plan";
import type { IStripeService } from "../service/stripe-service";

/** Stripe owns customer binding verification; tier selection is shared across consumers. */
type TierDeps = { stripe: IStripeService };

export type GetUserTierParams = TierDeps & { userId: string };

/**
 * Cross-service operation: determine a user's subscription tier.
 *
 * Resolves verified live subscriptions against recognized prices.
 */
export async function getUserTier({
  stripe,
  userId,
}: GetUserTierParams): Promise<SubscriptionTier> {
  try {
    // listSubscriptions verifies the user's exact configured customer binding.
    const subscriptions = await stripe.listSubscriptions(userId, {
      status: "active",
    });
    const tiers = subscriptions.map(subscriptionTier);
    const unidentified = subscriptions.filter(
      (sub, index) =>
        sub.status === "active" && tiers[index] === SubscriptionTier.FREE,
    ).length;
    if (unidentified)
      logger.warn("Active subscriptions have no recognized live plan", {
        count: unidentified,
      });
    return highestTier(tiers);
  } catch (error) {
    logger.error("Error determining user tier", {
      userId,
      errorType: error instanceof Error ? error.name : typeof error,
      errorMessage: error instanceof Error ? error.message : String(error),
    });
    return SubscriptionTier.FREE;
  }
}

/**
 * Convenience: the user's current tier limits in one call.
 */
export async function getUserTierLimits(
  params: GetUserTierParams,
): Promise<TierLimits> {
  const tier = await getUserTier(params);
  return getTierLimits(tier);
}
