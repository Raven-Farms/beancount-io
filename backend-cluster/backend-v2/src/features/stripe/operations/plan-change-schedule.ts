import Stripe from "stripe";
import { logger } from "@/shared/logger";
import type { PlanConfig } from "../service/stripe";
import { expandableId } from "../service/subscription-plan";

const scheduleLogger = logger.child({ module: "plan-change-schedule" });

/*
 * Stripe behaviour these helpers rely on, observed in test mode on API
 * 2025-12-15.clover:
 *
 * - A schedule made `from_subscription` has one phase, the current price to
 *   the period end; giving it a second phase creates no invoice, and the next
 *   invoice bills the new price.
 * - Discounts are carried by the subscription's discount ids. Passing the
 *   coupon instead would start a new discount and restart a limited one.
 * - While a schedule is attached, Stripe refuses a direct cancellation, and it
 *   accepts a direct price change that the schedule then undoes at renewal.
 *   Every other change therefore releases the schedule first.
 * - Scheduling a subscription whose cancellation is pending, with
 *   `end_behavior: release`, withdraws the cancellation.
 * - Releasing keeps the subscription on its current price and discounts.
 *
 * Callers read subscriptions with `schedule` expanded, so a schedule's status
 * and current phase need no extra request.
 */

async function loadSchedule(
  stripe: Stripe,
  schedule: string | Stripe.SubscriptionSchedule,
): Promise<Stripe.SubscriptionSchedule> {
  return typeof schedule === "string"
    ? stripe.subscriptionSchedules.retrieve(schedule)
    : schedule;
}

/**
 * Detach any schedule from the subscription, leaving its current price,
 * discounts and period untouched, so a direct update or cancellation is
 * neither refused nor undone later.
 */
export async function releaseSchedule(
  stripe: Stripe,
  subscription: Stripe.Subscription,
): Promise<void> {
  if (!subscription.schedule) return;
  const schedule = await loadSchedule(stripe, subscription.schedule);
  // A schedule that already ended or was released needs nothing.
  if (schedule.status === "active" || schedule.status === "not_started") {
    await stripe.subscriptionSchedules.release(schedule.id);
  }
}

async function attachSchedule(
  stripe: Stripe,
  subscription: Stripe.Subscription,
): Promise<Stripe.SubscriptionSchedule> {
  if (subscription.schedule) {
    return loadSchedule(stripe, subscription.schedule);
  }
  try {
    return await stripe.subscriptionSchedules.create({
      from_subscription: subscription.id,
    });
  } catch (error) {
    if (!(error instanceof Stripe.errors.StripeInvalidRequestError)) {
      throw error;
    }
    // A concurrent confirm may have attached one first; use it.
    const fresh = await stripe.subscriptions.retrieve(subscription.id, {
      expand: ["schedule"],
    });
    if (!fresh.schedule) throw error;
    scheduleLogger.info("Using the schedule a concurrent change attached", {
      subscriptionId: subscription.id,
    });
    return loadSchedule(stripe, fresh.schedule);
  }
}

/**
 * Keep the current price until the end of the paid period, then move `item`
 * to `target` with nothing charged now. Every other item, its quantity and
 * the discounts stay as they are. A schedule already attached (an earlier
 * pending change) has its phases replaced, so there is never more than one.
 * Returns when the new price takes effect: the period end, the same date the
 * preview reports.
 */
export async function scheduleChange(
  stripe: Stripe,
  subscription: Stripe.Subscription,
  item: Stripe.SubscriptionItem,
  target: PlanConfig,
): Promise<Date> {
  const schedule = await attachSchedule(stripe, subscription);
  const current = schedule.current_phase;
  if (!current) throw new Error("Subscription schedule has no current phase");
  const periodEnd = item.current_period_end;
  const discounts = subscription.discounts.map((discount) => ({
    discount: expandableId(discount),
  }));
  const items = (planPrice: string) =>
    subscription.items.data.map((each) => ({
      price: each.id === item.id ? planPrice : each.price.id,
      quantity: each.quantity ?? 1,
    }));
  await stripe.subscriptionSchedules.update(schedule.id, {
    end_behavior: "release",
    proration_behavior: "none",
    phases: [
      {
        items: items(item.price.id),
        start_date: current.start_date,
        end_date: periodEnd,
        discounts,
      },
      {
        items: items(target.priceId),
        duration: { interval: target.interval, interval_count: 1 },
        discounts,
        proration_behavior: "none",
      },
    ],
  });
  return new Date(periodEnd * 1000);
}
