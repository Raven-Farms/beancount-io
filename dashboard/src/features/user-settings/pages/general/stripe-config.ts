/** Live billing catalog. URL query parameters never select a different tenant. */
export const SUBSCRIPTION_TIERS = [
  "premium",
  "growth",
  "organization",
] as const;
export type SubscriptionTier = (typeof SUBSCRIPTION_TIERS)[number];
export const BILLING_CYCLES = ["monthly", "yearly"] as const;
export type BillingCycle = (typeof BILLING_CYCLES)[number];
/** Yearly is what Billing offers first (PRFAQ005). */
export const DEFAULT_BILLING_CYCLE: BillingCycle = "yearly";

export interface TierPricing {
  monthly: string;
  yearly: string;
  /** List prices in cents, as Stripe and `previewPlanChange` report them. */
  monthlyAmount: number;
  yearlyAmount: number;
}

export interface StripePlanConfig {
  clientId: string;
  premium: TierPricing;
  growth: TierPricing;
  organization: TierPricing;
}

export const stripePlanConfig: StripePlanConfig = {
  clientId: "beancount-web-prod",
  premium: {
    monthly: "price_1RrSOGEqsEqs2tLVFnyB34qG", // $14.99/month
    yearly: "price_1L9ccEEqsEqs2tLVbeBgHm9p", // $99.99/year (legacy)
    monthlyAmount: 1499,
    yearlyAmount: 9999,
  },
  growth: {
    monthly: "price_1SyPdaEqsEqs2tLViLPUDoVi", // $99.99/month
    yearly: "price_1SyPdbEqsEqs2tLV7PJyWZed", // $79.99/month billed yearly ($959.88/year)
    monthlyAmount: 9999,
    yearlyAmount: 95988,
  },
  organization: {
    monthly: "price_1SyPdcEqsEqs2tLVCWEgU1PZ", // $499.99/month
    yearly: "price_1SyPdfEqsEqs2tLVmK6zCrP6", // $399.99/month billed yearly ($4,799.88/year)
    monthlyAmount: 49999,
    yearlyAmount: 479988,
  },
};

/** Older prices still billed to existing subscribers but never offered again. */
export const LEGACY_PRICE_IDS: ReadonlySet<string> = new Set([
  "price_1L9ccEEqsEqs2tLVKPRV17wb", // $9.99/month Premium
]);

/** A tier's price on one cycle. */
export function cyclePrice(
  tier: SubscriptionTier,
  cycle: BillingCycle,
): { priceId: string; amount: number } {
  const pricing = stripePlanConfig[tier];
  return cycle === "yearly"
    ? { priceId: pricing.yearly, amount: pricing.yearlyAmount }
    : { priceId: pricing.monthly, amount: pricing.monthlyAmount };
}

/** What a year costs on monthly billing versus yearly, in cents. */
export function yearlySaving(tier: SubscriptionTier): {
  saving: number;
  percent: number;
} {
  const { monthlyAmount, yearlyAmount } = stripePlanConfig[tier];
  const twelveMonths = monthlyAmount * 12;
  const saving = twelveMonths - yearlyAmount;
  return { saving, percent: Math.round((saving / twelveMonths) * 100) };
}

/** The tier and cycle a current price sells, or null for any other price. */
export function planForPrice(
  priceId: string,
): { tier: SubscriptionTier; cycle: BillingCycle } | null {
  for (const tier of SUBSCRIPTION_TIERS) {
    for (const cycle of BILLING_CYCLES) {
      if (cyclePrice(tier, cycle).priceId === priceId) return { tier, cycle };
    }
  }
  return null;
}

/** What a price costs per month: a yearly price is spread over twelve. */
export function monthlyEquivalent(amount: number, cycle: BillingCycle): number {
  return cycle === "yearly" ? Math.round(amount / 12) : amount;
}
