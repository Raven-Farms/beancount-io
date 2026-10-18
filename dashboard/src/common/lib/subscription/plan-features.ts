import type { UserTier } from "@/common/hooks/use-user-limits";
import { TIER_RANK } from "./tier-config";

/**
 * The pricing table's plan features, by the lowest tier that includes each.
 * They are provided on request rather than switched by the API, so this list
 * mirrors the pricing page instead of a backend rule (PRFAQ005 question 21).
 */
export const PLAN_FEATURES: readonly { labelKey: string; minTier: UserTier }[] =
  [
    { labelKey: "userSettings.featureAutomaticBackups", minTier: "PREMIUM" },
    {
      labelKey: "userSettings.featureAutomationIntegrations",
      minTier: "GROWTH",
    },
    { labelKey: "userSettings.featureOidcSso", minTier: "ORGANIZATION" },
    { labelKey: "userSettings.featureMultiEntity", minTier: "ORGANIZATION" },
  ];

/** Features `to` includes that `from` does not. */
export function featuresGained(from: UserTier, to: UserTier): string[] {
  return PLAN_FEATURES.filter(
    ({ minTier }) =>
      TIER_RANK[minTier] > TIER_RANK[from] &&
      TIER_RANK[minTier] <= TIER_RANK[to],
  ).map(({ labelKey }) => labelKey);
}
