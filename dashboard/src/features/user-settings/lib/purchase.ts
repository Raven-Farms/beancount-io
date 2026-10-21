import { track } from "@/common/analytics";
import { planForPrice } from "../pages/general/stripe-config";
import { majorUnits } from "../pages/general/use-money-format";

const KEY_PREFIX = "beancount.purchase.";
// A Checkout confirmation link is opened within minutes; one opened a day
// later is a bookmark or another browser, whose purchase was already counted.
const CHECKOUT_CONFIRMATION_WINDOW_MS = 24 * 60 * 60 * 1000;
/** Ids recorded during this page load, for when storage is unavailable. */
const recordedThisLoad = new Set<string>();

export interface Purchase {
  /** The plan's Stripe invoice; GA4 deduplicates purchases on it. */
  invoiceId: string | null | undefined;
  /** What the invoice charges, in the currency's minor unit; may be 0. */
  amount: number | null | undefined;
  currency: string | null | undefined;
  priceId: string;
}

/**
 * Send GA4's `purchase` for a plan's invoice, once per browser, whatever it
 * charged. Returns true only the first time, so a caller that runs on page
 * load can celebrate exactly once. Without an invoice there is nothing to
 * deduplicate on, so nothing is sent.
 */
export function recordPurchase(purchase: Purchase): boolean {
  const { invoiceId, amount, currency, priceId } = purchase;
  if (!invoiceId || !currency || amount == null) return false;
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
