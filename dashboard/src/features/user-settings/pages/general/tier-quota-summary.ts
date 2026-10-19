import { type TierQuota } from "@/common/hooks/use-all-tier-quotas";

type Translate = (
  key: string,
  params?: Record<string, string | number>,
) => string;
type FormatCount = (value: number) => string;

/** One quota as a translated line; `-1` is unlimited. */
export function ledgersLine(
  max: number,
  t: Translate,
  formatCount: FormatCount,
) {
  return max === -1
    ? t("userSettings.unlimitedLedgers")
    : t("userSettings.includedLedgers", {
        count: max,
        formattedCount: formatCount(max),
      });
}

export function collaboratorsLine(
  max: number,
  t: Translate,
  formatCount: FormatCount,
) {
  return max === -1
    ? t("userSettings.unlimitedCollaborators")
    : t("userSettings.collaboratorsPerLedger", {
        count: max,
        formattedCount: formatCount(max),
      });
}

export function aiTokensLine(
  max: number,
  t: Translate,
  formatCount: FormatCount,
) {
  return max === -1
    ? t("userSettings.unlimitedAiTokens")
    : t("userSettings.aiTokensPerMonth", { count: formatCount(max) });
}

/**
 * A tier's quotas in one translated line ("500K AI tokens / month · 5 ledgers
 * · …"), shared by the plan banner and the post-Checkout confirmation so both
 * describe a plan in the app language.
 */
export function describeTierQuota(
  tierQuota: TierQuota,
  t: Translate,
  formatCount: FormatCount,
): string {
  return [
    aiTokensLine(tierQuota.aiCfoTokensMax, t, formatCount),
    ledgersLine(tierQuota.maxLedgers, t, formatCount),
    tierQuota.maxDirectives === -1
      ? t("userSettings.unlimitedDirectives")
      : t("userSettings.includedDirectives", {
          count: formatCount(tierQuota.maxDirectives),
        }),
    collaboratorsLine(tierQuota.maxCollaboratorsPerLedger, t, formatCount),
  ].join(" · ");
}
