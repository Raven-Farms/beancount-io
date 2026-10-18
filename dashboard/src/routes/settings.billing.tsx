import { createFileRoute } from "@tanstack/react-router";
import BillingSettingsPage from "@/features/user-settings/pages/billing";
import { createNoIndexHead } from "@/common/lib/seo/seo-helpers";

export const Route = createFileRoute("/settings/billing")({
  component: BillingSettingsPage,
  head: createNoIndexHead,
});
