import type { UserTier } from "@/common/hooks/use-user-limits";
import { TIER_RANK } from "./tier-config";

export type PlanInterval = "month" | "year";

/**
 * What choosing a plan would do, used only to label a button.
 *
 * The backend's `previewPlanChange` is the authority: it classifies the change
 * from the same rule (PRFAQ005 question 14) and returns what is charged and
 * when. This mirror exists so a plan row can say "Upgrade" or "Switch to
 * yearly" before anyone asks the server.
 */
export type PlanChoice =
  | "CURRENT"
  | "NEW"
  | "UPGRADE"
  | "TO_YEARLY"
  | "DOWNGRADE"
  | "TO_MONTHLY"
  | "SPLIT";

/** Choices that take effect now; the rest wait for the end of the period. */
export const IMMEDIATE_CHOICES: ReadonlySet<PlanChoice> = new Set([
  "NEW",
  "UPGRADE",
  "TO_YEARLY",
]);

export function planChoice(
  current: { tier: UserTier; interval: PlanInterval | null },
  target: { tier: UserTier; interval: PlanInterval | null },
): PlanChoice {
  const delta = TIER_RANK[target.tier] - TIER_RANK[current.tier];
  if (delta < 0) return "DOWNGRADE";
  // Free and Enterprise have no billing cycle; neither does a paid tier the
  // customer holds without a Stripe subscription.
  if (current.interval === null) {
    return delta === 0 ? "CURRENT" : "NEW";
  }
  if (target.interval === null) return delta === 0 ? "CURRENT" : "NEW";
  if (delta === 0) {
    if (current.interval === target.interval) return "CURRENT";
    return target.interval === "year" ? "TO_YEARLY" : "TO_MONTHLY";
  }
  if (current.interval === target.interval) return "UPGRADE";
  return target.interval === "year" ? "TO_YEARLY" : "SPLIT";
}
