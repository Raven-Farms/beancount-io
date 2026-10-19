import type Stripe from "stripe";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import type { PaidCustomer } from "../data/paid-customer-model/types";
import type { PlanConfig } from "../service/stripe";
import { customerId, holdsPaidTier } from "../service/subscription-plan";

export interface ActivePlan {
  subscription: Stripe.Subscription;
  item: Stripe.SubscriptionItem;
  plan: PlanConfig;
}

/**
 * The user's live billing binding for one client and every active
 * subscription item on a configured price, read fresh from Stripe.
 *
 * Preview and apply share this so a change is classified against exactly the
 * subscription it would move. More than one entry is a duplicate purchase.
 */
export async function loadActivePlans(
  {
    stripe,
    models,
    db,
  }: {
    stripe: Stripe;
    models: Pick<IModels, "paidCustomer">;
    db: DbExecutor;
  },
  userId: string,
  clientId: string,
  plans: PlanConfig[],
): Promise<{ binding: PaidCustomer | null; active: ActivePlan[] }> {
  const binding = await models.paidCustomer.findByUserIdAndClientId(
    db,
    userId,
    clientId,
  );
  const active: ActivePlan[] = [];
  if (!binding?.stripeCustomerId) return { binding, active };

  // Not canceled; holdsPaidTier then keeps active and past-due ones.
  const page = await stripe.subscriptions.list({
    customer: binding.stripeCustomerId,
    limit: 100,
    // A pending plan change lives on the schedule and a past-due grace on
    // the latest invoice; both come with the listing.
    expand: ["data.schedule", "data.latest_invoice"],
  });
  for (const subscription of page.data) {
    if (
      !holdsPaidTier(subscription) ||
      customerId(subscription.customer) !== binding.stripeCustomerId
    ) {
      continue;
    }
    for (const item of subscription.items.data) {
      const plan = plans.find((candidate) => candidate.priceId === item.price.id);
      if (plan) active.push({ subscription, item, plan });
    }
  }
  return { binding, active };
}
