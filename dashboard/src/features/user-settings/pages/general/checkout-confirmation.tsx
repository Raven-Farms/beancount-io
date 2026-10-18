import { CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/common/components/ui/button";
import type { ConfirmationState } from "./use-checkout-confirmation";

export function CheckoutConfirmation({
  state,
  planLabel,
  renewal,
  unlocked,
  returnTo,
  t,
  onRefresh,
  onDismiss,
}: {
  state: ConfirmationState;
  /** "Premium · Yearly" */
  planLabel: string;
  renewal: { date: string; amount: string } | null;
  unlocked: string | null;
  returnTo: string | null;
  t: (key: string, params?: Record<string, string | number>) => string;
  onRefresh: () => void;
  onDismiss: () => void;
}) {
  if (state === "confirming") {
    return (
      <div
        role="status"
        data-testid="checkout-confirmation"
        className="flex items-center gap-2 rounded-lg border p-4 text-sm"
      >
        <Loader2 className="h-4 w-4 animate-spin" />
        {t("userSettings.checkoutConfirming")}
      </div>
    );
  }
  if (state === "pending") {
    return (
      <div
        role="status"
        data-testid="checkout-confirmation"
        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4 text-sm"
      >
        <p>{t("userSettings.checkoutPending")}</p>
        <Button size="sm" variant="outline" onClick={onRefresh}>
          {t("userSettings.refresh")}
        </Button>
      </div>
    );
  }
  return (
    <div
      role="status"
      data-testid="checkout-confirmation"
      className="space-y-2 rounded-lg border border-primary/30 bg-primary/5 p-4"
    >
      <p className="flex items-center gap-2 text-sm font-semibold">
        <CheckCircle2 className="h-4 w-4 text-primary" />
        {t("userSettings.checkoutDone", { plan: planLabel })}
      </p>
      {renewal && (
        <p className="text-xs text-muted-foreground">
          {t("userSettings.checkoutRenews", renewal)}
        </p>
      )}
      {unlocked && (
        <p className="text-xs text-muted-foreground">
          {t("userSettings.checkoutUnlocked", { limits: unlocked })}
        </p>
      )}
      <div className="flex flex-wrap gap-2 pt-1">
        {returnTo && (
          <Button asChild size="sm">
            <a href={returnTo}>{t("userSettings.backToWork")}</a>
          </Button>
        )}
        <Button size="sm" variant="outline" onClick={onDismiss}>
          {t("userSettings.viewBilling")}
        </Button>
      </div>
    </div>
  );
}
