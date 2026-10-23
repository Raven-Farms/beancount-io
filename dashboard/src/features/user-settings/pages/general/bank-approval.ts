import type { PaymentIntent, Stripe, StripeError } from "@stripe/stripe-js";
import { stripePlanConfig } from "./stripe-config";

/**
 * What became of a payment the bank had to approve:
 * - `approved`: paid, so Stripe applies the held plan change.
 * - `declined`: the bank or the customer refused it; nothing changed.
 * - `pending`: still unsettled (a debit in flight, an approval left open).
 * - `unavailable`: Stripe.js could not run it here; use the hosted page.
 */
export type BankApproval = "approved" | "declined" | "pending" | "unavailable";

/**
 * Stripe.js, fetched from js.stripe.com only when a payment needs it: the
 * package injects Stripe's script when imported, so a static import would put
 * it on every page.
 */
async function loadStripeJs(): Promise<Stripe | null> {
  try {
    const { loadStripe } = await import("@stripe/stripe-js");
    return await loadStripe(stripePlanConfig.publishableKey);
  } catch {
    return null;
  }
}

/** A refusal leaves the PaymentIntent wanting another payment method. */
function isDecline(error: StripeError): boolean {
  return (
    error.type === "card_error" ||
    error.payment_intent?.status === "requires_payment_method"
  );
}

/**
 * Complete a plan change's payment in place: show the bank's challenge
 * (3D Secure and the like) over the page, or confirm the attached payment
 * method when the PaymentIntent was never confirmed. `returnUrl` is where a
 * redirect-only bank method comes back to.
 */
export async function approveBankPayment(
  clientSecret: string,
  returnUrl: string,
): Promise<BankApproval> {
  const stripe = await loadStripeJs();
  if (!stripe) return "unavailable";
  try {
    const current = await stripe.retrievePaymentIntent(clientSecret);
    if (!current.paymentIntent) return "unavailable";
    let outcome: { paymentIntent?: PaymentIntent; error?: StripeError } =
      current;
    if (current.paymentIntent.status === "requires_action") {
      outcome = await stripe.handleNextAction({ clientSecret });
    } else if (current.paymentIntent.status === "requires_confirmation") {
      outcome = await stripe.confirmPayment({
        clientSecret,
        confirmParams: { return_url: returnUrl },
        redirect: "if_required",
      });
    }
    if (outcome.error) {
      return isDecline(outcome.error) ? "declined" : "unavailable";
    }
    switch (outcome.paymentIntent?.status) {
      case "succeeded":
        return "approved";
      case "requires_payment_method":
      case "canceled":
        return "declined";
      default:
        return "pending";
    }
  } catch {
    return "unavailable";
  }
}
