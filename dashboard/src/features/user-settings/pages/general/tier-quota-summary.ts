import { type TierQuota } from "@/common/hooks/use-all-tier-quotas";

/**
 * A tier's quotas in one translated line ("500K AI tokens / month · 5 ledgers
 * · …"), shared by the plan banner and the post-Checkout confirmation so both
 * describe a plan in the app language.
 */
export function describeTierQuota(
  tierQuota: TierQuota,
  t: (key: string, params?: Record<string, string | number>) => string,
  formatCount: (value: number) => string,
): string {
  return [
    t("userSettings.aiTokensPerMonth", {
      count: formatCount(tierQuota.aiCfoTokensMax),
    }),
    tierQuota.maxLedgers === -1
      ? t("userSettings.unlimitedLedgers")
      : t("userSettings.includedLedgers", {
          count: tierQuota.maxLedgers,
          formattedCount: formatCount(tierQuota.maxLedgers),
        }),
    tierQuota.maxDirectives === -1
      ? t("userSettings.unlimitedDirectives")
      : t("userSettings.includedDirectives", {
          count: formatCount(tierQuota.maxDirectives),
        }),
    tierQuota.maxCollaboratorsPerLedger === -1
      ? t("userSettings.unlimitedCollaborators")
      : t("userSettings.collaboratorsPerLedger", {
          count: tierQuota.maxCollaboratorsPerLedger,
          formattedCount: formatCount(tierQuota.maxCollaboratorsPerLedger),
        }),
  ].join(" · ");
}
