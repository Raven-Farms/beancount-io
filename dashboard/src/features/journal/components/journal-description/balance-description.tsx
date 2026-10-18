import type { JournalBalance } from "@/common/types/journal";
import { formatAmountWithCurrency } from "./utils";
import { formatAmount } from "@/common/lib/format/format-amount";
import { useTranslations } from "@/common/hooks/use-translations";
import { Amount } from "@/common/components/amount";

interface BalanceDescriptionProps {
  directive: JournalBalance;
}

export function BalanceDescription({ directive }: BalanceDescriptionProps) {
  const { t } = useTranslations();
  const { amount, tolerance } = directive;
  return (
    <div className="flex-1 px-2 overflow-hidden">
      <div className="flex flex-wrap items-baseline gap-x-3 font-mono text-sm">
        <span className="break-all">{directive.account}</span>
        {amount && (
          <Amount className="tabular-nums">
            {tolerance
              ? `${formatAmount(amount.number)} ~ ${formatAmount(tolerance)} ${amount.currency}`
              : formatAmountWithCurrency(amount)}
          </Amount>
        )}
      </div>
      {directive.diff_amount && (
        <div className="text-sm text-muted-foreground">
          {t("journal.accumulated")}{" "}
          <Amount>{formatAmountWithCurrency(directive.diff_amount)}</Amount>
        </div>
      )}
    </div>
  );
}
