import type { UpgradeSurface } from "@/common/analytics";
import {
  DEFAULT_BILLING_CYCLE,
  type BillingCycle,
  type SubscriptionTier,
} from "@/features/user-settings/pages/general/stripe-config";

/**
 * Search parameters for `/settings/billing` that open the change sheet on a
 * plan; the contract is documented beside the route. A prompt that quoted a
 * monthly price passes `billing: "monthly"` so the sheet shows the price it
 * promised.
 */
export function billingLinkSearch({
  from,
  plan,
  billing = DEFAULT_BILLING_CYCLE,
  returnTo,
}: {
  from: UpgradeSurface;
  plan?: SubscriptionTier;
  billing?: BillingCycle;
  /** A safe same-origin path, offered back after the change. */
  returnTo?: string;
}) {
  return {
    ...(plan ? { plan, billing } : {}),
    from,
    ...(returnTo ? { return: returnTo } : {}),
  };
}
