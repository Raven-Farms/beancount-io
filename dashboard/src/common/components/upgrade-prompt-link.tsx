import type { ComponentProps } from "react";
import { Link } from "@tanstack/react-router";
import { track, type UpgradeSurface } from "@/common/analytics";
import { useSafeReturnPath } from "@/common/hooks/use-safe-return-path";
import { billingLinkSearch } from "@/common/lib/subscription/billing-link";
import type { TierInfo } from "@/common/lib/subscription/tier-config";
import type { BillingCycle } from "@/features/user-settings/pages/general/stripe-config";

/**
 * An in-product upgrade prompt's link: opens Billing's change sheet on the
 * recommended plan with the current page as the way back, and records
 * `upgrade_prompt_clicked`. Render it only where the prompt shows, so the
 * router subscription stays off pages that never offer an upgrade.
 */
export function UpgradePromptLink({
  surface,
  plan,
  billing,
  onClick,
  ...props
}: Omit<ComponentProps<"a">, "href"> & {
  surface: UpgradeSurface;
  /** Billing opens without a sheet when no plan is recommended. */
  plan: TierInfo | null;
  billing?: BillingCycle;
}) {
  const returnTo = useSafeReturnPath();
  return (
    <Link
      {...props}
      to="/settings/billing"
      search={billingLinkSearch({
        from: surface,
        plan: plan?.key,
        billing,
        returnTo,
      })}
      onClick={(event) => {
        onClick?.(event);
        track("upgrade_prompt_clicked", {
          surface,
          ...(plan ? { target_tier: plan.userTier } : {}),
        });
      }}
    />
  );
}
