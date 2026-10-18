import { z } from "zod";
import { getSafeRedirectPath } from "@/common/lib/auth/auth";
import { searchEnum, searchString } from "@/common/lib/search-params/tolerant";
import {
  BILLING_CYCLES,
  SUBSCRIPTION_TIERS,
} from "@/features/user-settings/pages/general/stripe-config";

/**
 * `/settings/billing` search parameters; the contract is documented beside the
 * route. A mistyped value renders Billing as if the parameter were absent
 * rather than failing the page, and `return` is kept only as a same-origin
 * path.
 */
export const billingSearchSchema = z.object({
  checkout: searchEnum(["success", "canceled"] as const),
  session_id: searchString(),
  return: searchString()
    .transform((path) => getSafeRedirectPath(path))
    .optional(),
  plan: searchEnum(SUBSCRIPTION_TIERS),
  billing: searchEnum(BILLING_CYCLES),
  from: searchString(),
});

export type BillingSearch = z.infer<typeof billingSearchSchema>;
