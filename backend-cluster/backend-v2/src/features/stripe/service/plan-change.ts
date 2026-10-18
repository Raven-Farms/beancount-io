import type { PlanConfig } from "./stripe";
import { tierRank } from "./subscription-plan";

/**
 * What choosing a price would do to the customer's current plan (PRFAQ005
 * question 14). Gains apply now; losses wait for the end of the paid period.
 *
 * - `NEW`: no subscription yet; the customer checks out.
 * - `UPGRADE`: a higher tier on the same billing cycle.
 * - `TO_YEARLY`: monthly to yearly, on the same or a higher tier.
 * - `DOWNGRADE`: a lower tier, on either cycle.
 * - `TO_MONTHLY`: yearly to monthly on the same tier.
 * - `SPLIT`: a higher tier while leaving yearly — a gain and a loss at once,
 *   so the customer chooses between the higher tier yearly now and the higher
 *   tier monthly from the renewal date.
 */
export type PlanChangeKind =
  | "NEW"
  | "UPGRADE"
  | "TO_YEARLY"
  | "DOWNGRADE"
  | "TO_MONTHLY"
  | "SPLIT";

/** Why a choice is refused before any Stripe work. */
export type PlanChangeRefusal =
  | "CURRENT_PLAN"
  | "SAME_TIER_AND_CYCLE"
  | "MULTIPLE_SUBSCRIPTIONS";

/** When a change takes effect, and through which Stripe mechanism. */
export type PlanChangeEffect = "CHECKOUT" | "IMMEDIATE" | "SCHEDULED";

export const PLAN_CHANGE_EFFECT: Record<PlanChangeKind, PlanChangeEffect> = {
  NEW: "CHECKOUT",
  UPGRADE: "IMMEDIATE",
  TO_YEARLY: "IMMEDIATE",
  DOWNGRADE: "SCHEDULED",
  TO_MONTHLY: "SCHEDULED",
  SPLIT: "SCHEDULED",
};

type PlanShape = Pick<PlanConfig, "priceId" | "tier" | "interval">;

export type PlanChangeClassification =
  | { kind: PlanChangeKind }
  | { refusal: PlanChangeRefusal };

/**
 * Classify a change from configuration alone. `current` is the plan of the
 * customer's one active subscription, or `null` when they have none.
 */
export function classifyPlanChange(
  current: PlanShape | null,
  target: PlanShape,
): PlanChangeClassification {
  if (!current) return { kind: "NEW" };
  if (current.priceId === target.priceId) return { refusal: "CURRENT_PLAN" };

  const tierDelta = tierRank(target.tier) - tierRank(current.tier);
  const sameCycle = current.interval === target.interval;

  if (tierDelta < 0) return { kind: "DOWNGRADE" };
  if (tierDelta === 0) {
    // Same tier and cycle at another price is a legacy subscriber choosing
    // today's price: it would only raise what they pay.
    if (sameCycle) return { refusal: "SAME_TIER_AND_CYCLE" };
    return { kind: target.interval === "year" ? "TO_YEARLY" : "TO_MONTHLY" };
  }
  if (sameCycle) return { kind: "UPGRADE" };
  return { kind: target.interval === "year" ? "TO_YEARLY" : "SPLIT" };
}
