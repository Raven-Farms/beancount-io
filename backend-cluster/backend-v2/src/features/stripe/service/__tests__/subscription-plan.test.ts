import type Stripe from "stripe";
import { expandedLatestInvoice, pastDueRetry } from "../subscription-plan";

const invoice = {
  id: "in_1",
  status: "open",
  next_payment_attempt: 1_800_000_000,
} as Stripe.Invoice;

describe("expandedLatestInvoice", () => {
  it.each([
    ["an expanded invoice", invoice, invoice],
    ["a bare id the request did not expand", "in_1", null],
    ["no invoice", null, null],
  ])("returns %s as %p", (_label, latest, expected) => {
    expect(
      expandedLatestInvoice({
        latest_invoice: latest as Stripe.Subscription["latest_invoice"],
      }),
    ).toBe(expected);
  });
});

describe("pastDueRetry", () => {
  const subscription = (
    status: Stripe.Subscription.Status,
    latest: Stripe.Subscription["latest_invoice"],
  ) => ({ status, latest_invoice: latest }) as Stripe.Subscription;

  it("reads the next retry from an expanded open invoice of a past-due subscription", () => {
    expect(pastDueRetry(subscription("past_due", invoice))).toBe(1_800_000_000);
  });

  it.each([
    ["an active subscription", subscription("active", invoice)],
    ["an unexpanded invoice", subscription("past_due", "in_1")],
    [
      "an invoice Stripe stopped retrying",
      subscription("past_due", { ...invoice, next_payment_attempt: null }),
    ],
  ])("has no retry for %s", (_label, sub) => {
    expect(pastDueRetry(sub)).toBeNull();
  });
});
