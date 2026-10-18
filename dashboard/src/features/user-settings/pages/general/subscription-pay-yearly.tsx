import { Button } from "@/common/components/ui/button";
import {
  cyclePrice,
  yearlySaving,
  type SubscriptionTier,
} from "./stripe-config";
import { useMoneyFormat } from "./use-money-format";

/**
 * The yearly offer on a monthly plan: the one line that makes the cheaper
 * cycle visible where a subscriber manages billing (PRFAQ005 question 1).
 */
export function PayYearlyOffer({
  tier,
  t,
  busy,
  onSwitch,
}: {
  tier: SubscriptionTier;
  t: (key: string, params?: Record<string, string | number>) => string;
  busy: boolean;
  onSwitch: () => void;
}) {
  const formatMoney = useMoneyFormat();
  const yearly = cyclePrice(tier, "yearly").amount;
  const monthlyTotal = cyclePrice(tier, "monthly").amount * 12;
  const { saving } = yearlySaving(tier);
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
