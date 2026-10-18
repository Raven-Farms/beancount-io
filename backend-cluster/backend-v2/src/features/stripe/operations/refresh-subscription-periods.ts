import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import type { IStripeService } from "../service/stripe-service";
import { SUBSCRIPTION_CONFIG } from "../service/stripe";
import {
  customerId,
  subscriptionPeriodEnd,
  SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
} from "../service/subscription-plan";

/** Read bindings before Stripe, then compare-and-set so a concurrent webhook wins. */
export async function refreshSubscriptionPeriods(
  stripe: IStripeService,
  models: Pick<IModels, "paidCustomer">,
  db: DbExecutor,
  userId: string,
  status: "active" | "all" = "active",
) {
  const bindings = await models.paidCustomer.findByUserId(db, userId);
  const subscriptions = await stripe.listSubscriptions(userId, {
    bindings,
    status,
  });
  for (const binding of bindings) {
    if (!SUBSCRIPTION_CONFIG[binding.clientId]) continue;
    const own = subscriptions.filter(
      (sub) =>
        sub.clientId === binding.clientId &&
        customerId(sub.customer) === binding.stripeCustomerId,
    );
    const period = subscriptionPeriodEnd(own);
    if (
      (binding.currentPeriodEnd?.getTime() ?? null) !==
        (period?.getTime() ?? null) ||
      binding.periodVerificationVersion !==
        SUBSCRIPTION_PERIOD_VERIFICATION_VERSION
    ) {
      await models.paidCustomer.updatePeriodIfUnchanged(
        db,
        binding,
        period,
        SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
      );
    }
  }
  return subscriptions;
}
