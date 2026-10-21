import type { JournalTransaction } from "../types";
import {
  isMixedPostingsAmount,
  selectTransactionAmount,
} from "../utils/transaction-display-utils";

/**
 * The signed amount a transaction row shows: `+` for money in, `-` for money
 * out, and unsigned when the entry has no direction (a zero, a transfer
 * between two cash accounts, or an entry with no cash posting at all).
 *
 * `text` is the unsigned figure from `formatAmount`, so the sign is added here;
 * the transaction detail hero signs through this same function. Without it a
 * negative entry read exactly like a positive one, and the rows under a
 * merchant stopped adding up to the total shown above them.
 */
export function formatEntryRowAmount(text: string, value: number): string {
  if (value > 0) return `+${text}`;
  if (value < 0) return `-${text}`;
  return text;
}

/**
 * What a transaction row shows on its trailing edge. A trade whose money side
 * spans several accounts reads as the neutral `mixedLabel`, never signed or
 * colored as an inflow; its exact postings are on the detail screen.
 */
export function selectEntryRowAmount(
  txn: JournalTransaction,
  mixedLabel: string,
  operatingCurrency?: string,
): { amountStr: string; isPositive: boolean | null } {
  const amount = selectTransactionAmount(txn, operatingCurrency);
  if (!amount) return { amountStr: "", isPositive: null };
  if (isMixedPostingsAmount(amount)) {
    return { amountStr: mixedLabel, isPositive: null };
  }
  return {
    amountStr: formatEntryRowAmount(amount.text, amount.value),
    isPositive: amount.value > 0,
  };
}
