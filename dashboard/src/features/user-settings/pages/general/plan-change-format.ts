import { tierInfoByKey } from "@/common/lib/subscription/tier-config";
import type { PreviewPlanChangeQuery } from "@/graphql/definitions";
import type { BillingCycle, SubscriptionTier } from "./stripe-config";

export type Translate = (
  key: string,
  params?: Record<string, string | number>,
) => string;
export type Preview = PreviewPlanChangeQuery["previewPlanChange"];

/** "Growth · Yearly", as the change sheet names a plan. */
export function planLabel(
  t: Translate,
  tier: SubscriptionTier,
  cycle: BillingCycle,
): string {
  return `${t(tierInfoByKey(tier).labelKey)} · ${t(
    cycle === "yearly" ? "userSettings.yearly" : "userSettings.monthly",
  )}`;
}

/** "Then $143.88/year, next on Oct 17, 2027.", or null without a date. */
export function nextChargeLine(
  t: Translate,
  formatMoney: (cents: number, currency?: string) => string,
  formatDate: (value: string | Date) => string,
  preview: Preview,
  cycle: BillingCycle,
): string | null {
  if (!preview.nextChargeAt) return null;
  return t("userSettings.planChangeNext", {
    amount: `${formatMoney(preview.nextAmount, preview.currency)}${t(
      cycle === "yearly" ? "userSettings.perYear" : "userSettings.perMonth",
    )}`,
    date: formatDate(preview.nextChargeAt),
  });
}
