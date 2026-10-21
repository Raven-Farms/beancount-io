import { formatLedgerDateShort } from "../../common/date-format";
import type { useTranslations } from "../../common/hooks/use-translations";
import { formatAmount } from "../transactions-screen/utils/transaction-display-utils";
import {
  cadenceLabelKey,
  type MerchantListItem,
} from "./selectors/merchant-sections";

type Translate = ReturnType<typeof useTranslations>["t"];

function primaryTypical(
  amounts: Record<string, number>,
): { currency: string; amount: number } | null {
  const entries = Object.entries(amounts);
  if (entries.length === 0) {
    return null;
  }
  entries.sort((a, b) => Math.abs(b[1]!) - Math.abs(a[1]!));
  const [currency, amount] = entries[0]!;
  return { currency, amount };
}

/**
 * Everything a Merchants row says, and the label VoiceOver reads for it. The
 * label was the payee alone, so a row showing "Netflix · Monthly · ~$15.99 ·
 * Overdue" read "Netflix, button" (w21/139). It now says what the row shows,
 * plus the count and "Recurring" a Recurring-section row leaves to its
 * section header.
 */
export function merchantRowText(
  item: MerchantListItem,
  t: Translate,
  locale: string,
) {
  const { merchant, resolved, inRecurringSection } = item;
  const showBadge = resolved.isRecurring && !inRecurringSection;
  const detection = resolved.detection;

  const countLabel = t("merchantsTransactionCount", {
    count: merchant.transactionCount,
  });
  const lastDate = merchant.lastDate
    ? formatLedgerDateShort(merchant.lastDate, locale)
    : "";

  let subtitle = countLabel;
  let cadenceLabel: string | null = null;
  let trailingAmount: string | null = null;
  let trailingMeta: string | null = lastDate || null;
  let trailingOverdue = false;

  if (inRecurringSection && resolved.isRecurring) {
    const cadenceKey = cadenceLabelKey(resolved.cadence);
    cadenceLabel = cadenceKey ? t(cadenceKey) : "";
    const typical = detection
      ? primaryTypical(detection.typicalAmountByCurrency)
      : null;
    trailingAmount = typical
      ? `${detection?.isApproximate ? "~" : ""}${formatAmount(typical.amount, typical.currency)}`
      : null;
    subtitle = cadenceLabel;
    if (detection?.nextExpected) {
      const next = formatLedgerDateShort(detection.nextExpected, locale);
      if (detection.isOverdue) {
        trailingMeta = t("merchantsOverdue");
        trailingOverdue = true;
      } else {
        trailingMeta = t("merchantsNextExpected", { date: next });
      }
    } else {
      trailingMeta = null;
    }
  }

  const accessibilityLabel = [
    merchant.payee,
    countLabel,
    resolved.isRecurring ? t("merchantsRecurringBadge") : null,
    cadenceLabel,
    trailingAmount,
    trailingMeta,
  ]
    .filter((part): part is string => !!part)
    .join(", ");

  return {
    showBadge,
    subtitle,
    lastDate,
    trailingAmount,
    trailingMeta,
    trailingOverdue,
    accessibilityLabel,
  };
}
