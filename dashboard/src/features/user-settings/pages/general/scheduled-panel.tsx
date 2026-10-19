import { useId } from "react";
import { CalendarClock } from "lucide-react";
import { Button } from "@/common/components/ui/button";
import type { GetSubscriptionStatusQuery } from "@/graphql/definitions";
import { planForPrice } from "./stripe-config";
import { planLabel, type Translate } from "./plan-change-format";
import { useBillingDateFormat } from "./use-money-format";
import { isPendingCancellation } from "./subscription-state";

type SubscriptionStatus =
  GetSubscriptionStatusQuery["subscriptionStatus"]["subscriptions"][number];

/**
 * What is set to happen at the end of the paid period, with the action that
 * undoes it (PRFAQ005 question 15): a scheduled plan change and **Keep
 * current**, or a cancellation and **Resume**. Nothing pending renders
 * nothing.
 */
export function ScheduledPanel({
  subscription,
  currentName,
  busy,
  t,
  onKeepCurrent,
  onResume,
}: {
  subscription: SubscriptionStatus;
  /** The current plan, e.g. "Premium · Monthly". */
  currentName: string;
  busy: boolean;
  t: Translate;
  /** Gets the plan the undone change would have moved to, when known. */
  onKeepCurrent: (target: ReturnType<typeof planForPrice>) => void;
  onResume: () => void;
}) {
  const formatDate = useBillingDateFormat();
  const headingId = useId();
  const scheduled = subscription.scheduledChange;
  const target = scheduled ? planForPrice(scheduled.priceId) : null;

  let message: string;
  let action: { label: string; onClick: () => void };
  if (isPendingCancellation(subscription)) {
    message = t("userSettings.scheduledEnds", {
      plan: currentName,
      date: formatDate(subscription.cancelAt ?? subscription.currentPeriodEnd),
    });
    action = { label: t("userSettings.resumeSubscription"), onClick: onResume };
  } else if (scheduled) {
    message = t("userSettings.scheduledChangesTo", {
      plan: target
        ? planLabel(t, target.tier, target.cycle)
        : t("userSettings.unknownPlan"),
      date: formatDate(scheduled.effectiveAt),
    });
    action = {
      label: t("userSettings.scheduledKeepCurrent"),
      onClick: () => onKeepCurrent(target),
    };
  } else {
    return null;
  }

  return (
    <section
      aria-labelledby={headingId}
      className="rounded-md border p-3"
      data-testid="scheduled-panel"
    >
      <h3
        id={headingId}
        className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground"
      >
        <CalendarClock aria-hidden className="h-3.5 w-3.5" />
        {t("userSettings.scheduledHeading")}
      </h3>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <p>{message}</p>
        <Button
          size="sm"
          variant="outline"
          disabled={busy}
          onClick={action.onClick}
        >
          {action.label}
        </Button>
      </div>
    </section>
  );
}
