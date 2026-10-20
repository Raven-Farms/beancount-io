import { track } from "@/common/analytics";
import { planForPrice } from "../pages/general/stripe-config";

const KEY_PREFIX = "beancount.purchase.";
/** Ids recorded during this page load, for when storage is unavailable. */
const recordedThisLoad = new Set<string>();

export interface PaidTransaction {
  /** The Stripe invoice that was paid; GA4 deduplicates purchases on it. */
  invoiceId: string | null | undefined;
  /** Minor units, discounts applied, as Stripe reports them. */
  amountPaid: number | null | undefined;
  currency: string | null | undefined;
  priceId: string;
}

/**
 * Send GA4's `purchase` for a paid invoice, once per browser. The browser is
 * the only purchase source, so the caller celebrates exactly the purchases
 * this counts: it returns true only the first time. A missing invoice, a
 * zero amount or an invoice already recorded sends nothing.
 */
export function recordPaidTransaction(transaction: PaidTransaction): boolean {
  const { invoiceId, amountPaid, currency, priceId } = transaction;
  if (!invoiceId || !currency || !amountPaid || amountPaid <= 0) return false;
  if (!claim(invoiceId)) return false;
  // Billing is in USD everywhere, a two-decimal currency.
  const value = amountPaid / 100;
  const plan = planForPrice(priceId);
  track("purchase", {
    transaction_id: invoiceId,
    value,
    currency: currency.toUpperCase(),
    items: [
      {
        item_id: priceId,
        item_name: plan?.tier ?? "unknown",
        item_variant: plan?.cycle === "yearly" ? "year" : "month",
        price: value,
        quantity: 1,
      },
    ],
  });
  return true;
}

function claim(invoiceId: string): boolean {
  if (recordedThisLoad.has(invoiceId)) return false;
  recordedThisLoad.add(invoiceId);
  try {
    const key = KEY_PREFIX + invoiceId;
    if (window.localStorage.getItem(key)) return false;
    window.localStorage.setItem(key, "1");
  } catch {
    // Without storage, once per page load is the best available.
  }
  return true;
}
