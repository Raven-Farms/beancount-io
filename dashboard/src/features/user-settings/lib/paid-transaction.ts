import { track } from "@/common/analytics";
import { planForPrice } from "../pages/general/stripe-config";
import { majorUnits } from "../pages/general/use-money-format";

const KEY_PREFIX = "beancount.purchase.";
// A Checkout confirmation link is opened within minutes; one opened a day
// later is a bookmark or another browser, whose purchase was already counted.
const CHECKOUT_CONFIRMATION_WINDOW_MS = 24 * 60 * 60 * 1000;
/** Ids recorded during this page load, for when storage is unavailable. */
const recordedThisLoad = new Set<string>();

export interface PaidTransaction {
  /** The Stripe invoice that was paid; GA4 deduplicates purchases on it. */
  invoiceId: string | null | undefined;
  /** Collected, in the currency's minor unit, discounts applied. */
  amount: number | null | undefined;
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
  const { invoiceId, amount, currency, priceId } = transaction;
  if (!invoiceId || !currency || !amount || amount <= 0) return false;
  if (!claim(invoiceId)) return false;
  const value = majorUnits(amount, currency);
  const plan = planForPrice(priceId);
  track("purchase", {
    transaction_id: invoiceId,
    value,
    currency: currency.toUpperCase(),
    items: [
      {
        item_id: priceId,
        item_name: plan?.tier ?? "unknown",
        // An unknown price has no cycle to report.
        ...(plan && {
          item_variant: plan.cycle === "yearly" ? "year" : "month",
        }),
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

/** Whether a Checkout's first invoice is recent enough to count on return. */
export function isFreshCheckoutInvoice(
  created: string | Date,
  now = Date.now(),
): boolean {
  const age = now - new Date(created).getTime();
  return age >= 0 && age <= CHECKOUT_CONFIRMATION_WINDOW_MS;
}
