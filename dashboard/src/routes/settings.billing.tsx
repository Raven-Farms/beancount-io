import { createFileRoute } from "@tanstack/react-router";
import BillingSettingsPage from "@/features/user-settings/pages/billing";
import { billingSearchSchema } from "@/features/user-settings/lib/billing-search";
import { createNoIndexHead } from "@/common/lib/seo/seo-helpers";

export const Route = createFileRoute("/settings/billing")({
  component: BillingSettingsPage,
  validateSearch: (search) => billingSearchSchema.parse(search),
  head: createNoIndexHead,
});
