import { Button } from "@/common/components/ui/button";
import { cyclePrice, type SubscriptionTier } from "./stripe-config";
import { useMoneyFormat } from "./use-money-format";

/**
 * The yearly offer on a monthly plan: the one line that makes the cheaper
 * cycle visible where a subscriber manages billing (PRFAQ005 question 1).
 * It compares twelve of what this subscriber pays, not the list price, so a
 * legacy monthly price that already beats yearly gets no offer at all.
 */
export function PayYearlyOffer({
  tier,
  monthlyAmount,
  t,
  busy,
  onSwitch,
}: {
  tier: SubscriptionTier;
  /** The subscriber's own monthly price, in cents. */
  monthlyAmount: number;
  t: (key: string, params?: Record<string, string | number>) => string;
  busy: boolean;
  onSwitch: () => void;
}) {
  const formatMoney = useMoneyFormat();
  const yearly = cyclePrice(tier, "yearly").amount;
  const monthlyTotal = monthlyAmount * 12;
  const saving = monthlyTotal - yearly;
  if (saving <= 0) return null;
  return (
    <div
      data-testid="pay-yearly-offer"
      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-dashed border-primary/40 bg-primary/5 p-3"
    >
      <p className="text-sm">
        {t("userSettings.payYearlyOffer", {
          yearly: formatMoney(yearly),
          monthlyTotal: formatMoney(monthlyTotal),
          saving: formatMoney(saving),
        })}
      </p>
      <Button size="sm" disabled={busy} onClick={onSwitch}>
        {t("userSettings.switchToYearly")}
      </Button>
    </div>
  );
}
