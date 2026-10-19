import Stripe from "stripe";
import { logger } from "@/shared/logger";
import { ValidationError } from "@/shared/errors";
import { REFUSAL_MESSAGES } from "../service/plan-change";
import { SUBSCRIPTION_CONFIG, type PlanConfig } from "../service/stripe";
import { expandableId } from "../service/subscription-plan";
import { loadActivePlans } from "./current-plan";

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

export interface ScheduledChangeView {
  priceId: string;
  effectiveAt: Date;
}

/**
 * The plan change a subscription's schedule will make, or null: the first
 * phase after the current one that moves the subscription to another price.
 * A schedule in its last phase (the change already took effect) has nothing
 * pending. The schedule must be expanded; an id cannot say what it holds.
 */
export function pendingChange(
  subscription: Stripe.Subscription,
  plans: readonly PlanConfig[],
): ScheduledChangeView | null {
  const schedule = subscription.schedule;
  if (!schedule) return null;
  if (typeof schedule === "string") {
    throw new Error("Read the subscription with its schedule expanded");
  }
  const current = schedule.current_phase;
  if (schedule.status !== "active" || !current) return null;
  const currentPrices = new Set(
    subscription.items.data.map((item) => item.price.id),
  );
  for (const phase of schedule.phases) {
    if (phase.start_date < current.end_date) continue;
    const added = phase.items
      .map((item) => expandableId(item.price))
      .filter((id) => !currentPrices.has(id));
    // Name the plan the phase moves to, else whatever price it adds.
    const priceId =
      added.find((id) => plans.some((plan) => plan.priceId === id)) ?? added[0];
    if (priceId) {
      return { priceId, effectiveAt: new Date(phase.start_date * 1000) };
    }
  }
  return null;
}

/**
 * Undo a pending plan change: release the schedule holding it. The
 * subscription keeps its current price, discounts and period. Nothing pending
 * is a success, so a repeated undo is harmless.
 */
export async function cancelScheduledChange(
  deps: Parameters<typeof loadActivePlans>[0],
  userId: string,
  clientId: string,
): Promise<{ success: boolean; message: string }> {
  const plans = SUBSCRIPTION_CONFIG[clientId]?.plans;
  if (!plans) throw new ValidationError("clientId", "Unknown client");
  const { active } = await loadActivePlans(deps, userId, clientId, plans);
  if (active.length > 1) {
    return {
      success: false,
      message: REFUSAL_MESSAGES.MULTIPLE_SUBSCRIPTIONS,
    };
  }
  const subscription = active[0]?.subscription;
  if (!subscription || !pendingChange(subscription, plans)) {
    return { success: true, message: "No plan change is scheduled." };
  }
  await releaseSchedule(deps.stripe, subscription);
  return {
    success: true,
    message:
      "Your scheduled plan change was cancelled. Your current plan continues.",
  };
}
