/**
 * Presentation for one merchant-header currency total.
 *
 * The totals query returns the payee's signed net Expenses/Income sum per
 * currency, so the minus is the only thing telling a refund or income-heavy
 * merchant (Broker, an employer) apart from an expense of the same size. The
 * global `formatMoneyWithCurrency` is deliberately unsigned, so the header
 * uses the signed formatter instead — without a "+" on non-negative totals.
 *
 * A total that rounds to zero cents shows unsigned ("$0.00", never "-$0.00").
 *
 * Free of `@/` value imports so the jest-lite runner can require it.
 */

import { getCurrencySymbol } from "../../../common/currency-util";
import {
  formatSignedMoneyWithCode,
  formatSignedMoneyWithCurrency,
} from "../../../common/number-utils";
import type { MerchantCurrencyTotal } from "./merchant-stats";

export function formatMerchantTotal({
  total,
  currency,
}: MerchantCurrencyTotal): string {
  const shown = Math.abs(total) < 0.005 ? 0 : total;
  return formatSignedMoneyWithCurrency(shown, currency);
}

/**
 * The header's total lines. `$` is the symbol of USD, CAD, AUD and MXN, `¥` of
 * CNY and JPY, `kr` of SEK, NOK and DKK, so a merchant paid in two of them read
 * two identical "$42.50" lines (w21/535). A currency whose symbol another total
 * shares keeps it only when it is the ledger's primary currency; the others read
 * by code ("42.50 CAD").
 */
export function formatMerchantTotals(
  totals: readonly MerchantCurrencyTotal[],
  primaryCurrency?: string,
): string[] {
  return totals.map((row) => {
    const symbol = getCurrencySymbol(row.currency);
    const shared =
      symbol !== "" &&
      totals.some(
        (other) =>
          other.currency !== row.currency &&
          getCurrencySymbol(other.currency) === symbol,
      );
    if (!shared || row.currency === primaryCurrency) {
      return formatMerchantTotal(row);
    }
    const shown = Math.abs(row.total) < 0.005 ? 0 : row.total;
    return formatSignedMoneyWithCode(shown, row.currency);
  });
}
