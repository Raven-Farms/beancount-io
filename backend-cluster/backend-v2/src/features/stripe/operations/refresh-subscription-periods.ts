import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import type {
  IStripeService,
  SubscriptionListOptions,
} from "../service/stripe-service";
import { SUBSCRIPTION_CONFIG } from "../service/stripe";
import {
  customerId,
  highestTier,
  subscriptionPeriodEnd,
  subscriptionTier,
  SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
} from "../service/subscription-plan";

/** Read bindings before Stripe, then compare-and-set so a concurrent webhook wins. */
export async function refreshSubscriptionPeriods(
  stripe: IStripeService,
  models: Pick<IModels, "paidCustomer">,
  db: DbExecutor,
  userId: string,
  {
    // Non-canceled subscriptions: a past-due one still holds its paid period.
    status = "current",
    expandForStatus = false,
  }: Pick<SubscriptionListOptions, "status" | "expandForStatus"> = {},
) {
  const bindings = await models.paidCustomer.findByUserId(db, userId);
  const subscriptions = await stripe.listSubscriptions(userId, {
    bindings,
    status,
    expandForStatus,
  });
  for (const binding of bindings) {
    if (!SUBSCRIPTION_CONFIG[binding.clientId]) continue;
    const own = subscriptions.filter(
      (sub) =>
        sub.clientId === binding.clientId &&
        customerId(sub.customer) === binding.stripeCustomerId,
    );
    const period = subscriptionPeriodEnd(own);
    const tier = period ? highestTier(own.map(subscriptionTier)) : null;
    if (
      (binding.currentPeriodEnd?.getTime() ?? null) !==
        (period?.getTime() ?? null) ||
      (binding.periodTier ?? null) !== tier ||
      binding.periodVerificationVersion !==
        SUBSCRIPTION_PERIOD_VERIFICATION_VERSION
    ) {
      await models.paidCustomer.updatePeriodIfUnchanged(
        db,
        binding,
        period,
        SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
        tier,
      );
    }
  }
  return subscriptions;
}
