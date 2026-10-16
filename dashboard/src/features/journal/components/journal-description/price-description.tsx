import type { JournalPrice } from "@/common/types/journal";
import { formatAmountWithCurrency } from "./utils";
import { Amount } from "@/common/components/amount";

interface PriceDescriptionProps {
  directive: JournalPrice;
}

export function PriceDescription({ directive }: PriceDescriptionProps) {
  return (
    <div className="flex-1 px-2 overflow-hidden">
      <div className="font-mono text-sm break-all cursor-pointer">
        <Amount>
          {formatAmountWithCurrency(directive.amount)}/{directive.currency}
        </Amount>
      </div>
    </div>
  );
}
