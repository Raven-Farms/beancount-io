import type Stripe from "stripe";
import {
  renewalEmailSubject,
  renderRenewalHtml,
  renderRenewalText,
  type RenewalEmailParams,
} from "@/shared/email-templates";
import { SUBSCRIPTION_CONFIG, type PlanConfig } from "../service/stripe";
import { expandableId } from "../service/subscription-plan";
import {
  longDate,
  money,
  planName,
  sendBillingEmailOnce,
  type BillingEmailDeps,
} from "./billing-email";

export type RenewalEmailOutcome =
  | "sent"
  | "already-sent"
  | "no-recipient"
  | "not-applicable";

/**
 * The plan an invoice bills, from its lines, or undefined when none of its
 * prices is ours: the Stripe account bills other products too.
 */
export function invoicePlan(
  invoice: Stripe.Invoice,
  plans: readonly PlanConfig[],
): PlanConfig | undefined {
  for (const line of invoice.lines.data) {
    const price = line.pricing?.price_details?.price;
    const plan =
      price && plans.find((each) => each.priceId === expandableId(price));
    if (plan) return plan;
  }
  return undefined;
}

export type FailedRenewal = { invoiceId: string } & (
  | { kind: "failed"; nextAttemptAt: Date }
  | { kind: "final" }
);

/**
 * Which email a failed renewal charge calls for: `failed` after the first
 * attempt, `final` once Stripe has no retry left (the account then cancels
 * the subscription), nothing for the retries in between. Plan changes are
 * paid inside the change sheet and are not renewals.
 */
export function failedRenewal(invoice: Stripe.Invoice): FailedRenewal | null {
  const invoiceId = invoice.id;
  if (!invoiceId || invoice.billing_reason !== "subscription_cycle") {
    return null;
  }
  if (invoice.next_payment_attempt == null) return { invoiceId, kind: "final" };
  return invoice.attempt_count === 1
    ? {
        invoiceId,
        kind: "failed",
        nextAttemptAt: new Date(invoice.next_payment_attempt * 1000),
      }
    : null;
}

/** Tell the subscriber a renewal charge failed (w1/m40/t015). */
export async function emailFailedRenewal(
  deps: BillingEmailDeps,
  userId: string,
  clientId: string,
  invoice: Stripe.Invoice,
  plan: PlanConfig,
  failure: FailedRenewal,
): Promise<RenewalEmailOutcome> {
  const base = {
    plan: planName(plan),
    amount: money(invoice.amount_due, invoice.currency),
    billingUrl: SUBSCRIPTION_CONFIG[clientId].portalReturnUrl,
  };
  const params: RenewalEmailParams =
    failure.kind === "final"
      ? { ...base, kind: "final" }
      : {
          ...base,
          kind: "failed",
          nextAttemptDate: longDate(failure.nextAttemptAt),
        };
  return sendBillingEmailOnce(
    deps,
    userId,
    `renewal-${failure.kind}:${failure.invoiceId}`,
    {
      subject: renewalEmailSubject(params),
      html: renderRenewalHtml(params),
      text: renderRenewalText(params),
    },
  );
}

/**
 * Remind a yearly subscriber of the coming renewal and its charge, from
 * Stripe's upcoming-invoice notice. A monthly plan, a plan set to end, a
 * renewal that charges nothing, and one bringing a scheduled plan change
 * (which has its own reminder) get none.
 */
export async function emailRenewalReminder(
  deps: BillingEmailDeps,
  userId: string,
  clientId: string,
  invoice: Stripe.Invoice,
  subscription: Stripe.Subscription,
): Promise<RenewalEmailOutcome> {
  const { plans, portalReturnUrl } = SUBSCRIPTION_CONFIG[clientId];
  const item = subscription.items.data.find((each) =>
    plans.some((plan) => plan.priceId === each.price.id),
  );
  const plan = item && plans.find((each) => each.priceId === item.price.id);
  if (
    !item ||
    plan?.interval !== "year" ||
    subscription.cancel_at_period_end ||
    invoice.amount_due <= 0
  ) {
    return "not-applicable";
  }
  const renewsAt = new Date(item.current_period_end * 1000);
  const params: RenewalEmailParams = {
    kind: "upcoming",
    plan: planName(plan),
    amount: money(invoice.amount_due, invoice.currency),
    renewalDate: longDate(renewsAt),
    billingUrl: portalReturnUrl,
  };
  return sendBillingEmailOnce(
    deps,
    userId,
    `renewal-upcoming:${subscription.id}:${renewsAt.toISOString()}`,
    {
      subject: renewalEmailSubject(params),
      html: renderRenewalHtml(params),
      text: renderRenewalText(params),
    },
  );
}
