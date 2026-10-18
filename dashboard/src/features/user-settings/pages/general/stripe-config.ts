/** Live billing catalog. URL query parameters never select a different tenant. */
export type SubscriptionTier = "premium" | "growth" | "organization";
export interface TierPricing {
  monthly: string;
  yearly: string;
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
  },
  growth: {
    monthly: "price_1SyPdaEqsEqs2tLViLPUDoVi", // $99.99/month
    yearly: "price_1SyPdbEqsEqs2tLV7PJyWZed", // $79.99/month billed yearly ($959.88/year)
  },
  organization: {
    monthly: "price_1SyPdcEqsEqs2tLVCWEgU1PZ", // $499.99/month
    yearly: "price_1SyPdfEqsEqs2tLVmK6zCrP6", // $399.99/month billed yearly ($4,799.88/year)
  },
};
