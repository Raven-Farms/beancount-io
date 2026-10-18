import { z } from "zod";
import { searchEnum, searchString } from "@/common/lib/search-params/tolerant";

/**
 * `/settings/billing` search parameters. Stripe Checkout returns here with
 * `checkout=success&session_id=…`; a mistyped value renders Billing as if the
 * parameter were absent rather than failing the page.
 */
export const billingSearchSchema = z.object({
  checkout: searchEnum(["success", "canceled"] as const),
  session_id: searchString(),
  return: searchString(),
});

export type BillingSearch = z.infer<typeof billingSearchSchema>;
