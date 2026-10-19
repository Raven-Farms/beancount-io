import type Stripe from "stripe";
import {
  renewalEmailSubject,
  renderRenewalHtml,
  renderRenewalText,
  type RenewalEmailParams,
} from "@/shared/email-templates";
import { logger } from "@/shared/logger";
import { SUBSCRIPTION_CONFIG, type PlanConfig } from "../service/stripe";
import { expandableId, planItem } from "../service/subscription-plan";
import {
  longDate,
  money,
  planName,
  sendBillingEmailOnce,
  type BillingEmailDeps,
  type BillingEmailOutcome,
  type BillingMail,
} from "./billing-email";

const renewalLogger = logger.child({ module: "renewal-email" });

function render(params: RenewalEmailParams): BillingMail {
  return {
    subject: renewalEmailSubject(params),
    html: renderRenewalHtml(params),
    text: renderRenewalText(params),
  };
}

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

/**
 * A renewal's first failed charge, the one failure worth an email: later
 * retries repeat the news, and plan changes are paid inside the change sheet.
 */
export function isFirstFailedRenewal(
  invoice: Stripe.Invoice,
): invoice is Stripe.Invoice & { id: string } {
  return (
    !!invoice.id &&
    invoice.billing_reason === "subscription_cycle" &&
    invoice.attempt_count === 1
  );
}

/**
 * Whether the invoice's charge is waiting for the customer's bank to
 * authenticate it. Stripe's own confirm-payment email covers that case with
 * the link that completes it, so ours would only mislead. A lookup failure
 * answers false: a possibly redundant email beats a missing one.
 */
export async function awaitsAuthentication(
  stripe: Stripe,
  invoiceId: string,
): Promise<boolean> {
  try {
    const payments = await stripe.invoicePayments.list({
      invoice: invoiceId,
      expand: ["data.payment.payment_intent"],
    });
    return payments.data.some(({ payment }) => {
      const intent = payment.payment_intent;
      return (
        !!intent &&
        typeof intent !== "string" &&
        (intent.status === "requires_action" ||
          intent.last_payment_error?.code === "authentication_required")
      );
    });
  } catch (error) {
    renewalLogger.warn("Could not read a failed renewal's payments", {
      errorMessage: error instanceof Error ? error.message : String(error),
    });
    return false;
  }
}

/** Tell the subscriber a renewal's first charge failed. */
export function emailFailedRenewal(
  deps: BillingEmailDeps,
  userId: string,
  clientId: string,
  invoice: Stripe.Invoice & { id: string },
  plan: PlanConfig,
): Promise<Exclude<BillingEmailOutcome, "not-applicable">> {
  const retryAt = invoice.next_payment_attempt;
  return sendBillingEmailOnce(
    deps,
    userId,
    `renewal-failed:${invoice.id}`,
    render({
      kind: "failed",
      plan: planName(plan),
      amount: money(invoice.amount_due, invoice.currency),
      nextAttemptDate:
        retryAt == null ? null : longDate(new Date(retryAt * 1000)),
      billingUrl: SUBSCRIPTION_CONFIG[clientId].portalReturnUrl,
    }),
  );
}

/**
 * Tell the subscriber their plan ended because its renewal could not be
 * collected. Stripe names that reason only on the cancellation itself; the
 * last failed charge cannot, since a charge with no retry left also
 * describes one still waiting on the customer.
 */
export async function emailPlanEnded(
  deps: BillingEmailDeps,
  userId: string,
  clientId: string,
  subscription: Stripe.Subscription,
): Promise<BillingEmailOutcome> {
  const { plans, portalReturnUrl } = SUBSCRIPTION_CONFIG[clientId];
  const billed = planItem(subscription, plans);
  if (
    !billed ||
    subscription.status !== "canceled" ||
    subscription.cancellation_details?.reason !== "payment_failed"
  ) {
    return "not-applicable";
  }
  return sendBillingEmailOnce(
    deps,
    userId,
    `renewal-final:${subscription.id}`,
    render({
      kind: "final",
      plan: planName(billed.plan),
      billingUrl: portalReturnUrl,
    }),
  );
}

/**
 * Remind a yearly subscriber of the coming renewal and its charge, from
 * Stripe's upcoming-invoice notice. A monthly plan, a plan set to end by
 * then, a renewal that charges nothing, and one bringing a scheduled plan
 * change (which has its own reminder) get none.
 */
export async function emailRenewalReminder(
  deps: BillingEmailDeps,
  userId: string,
  clientId: string,
  invoice: Stripe.Invoice,
  subscription: Stripe.Subscription,
): Promise<BillingEmailOutcome> {
  const { plans, portalReturnUrl } = SUBSCRIPTION_CONFIG[clientId];
  const billed = planItem(subscription, plans);
  if (!billed || billed.plan.interval !== "year") return "not-applicable";
  const renewsAt = new Date(billed.item.current_period_end * 1000);
  const { cancel_at } = subscription;
  if (
    subscription.cancel_at_period_end ||
    (cancel_at != null && cancel_at * 1000 <= renewsAt.getTime()) ||
    invoice.amount_due <= 0
  ) {
    return "not-applicable";
  }
  return sendBillingEmailOnce(
    deps,
    userId,
    `renewal-upcoming:${subscription.id}:${renewsAt.toISOString()}`,
    render({
      kind: "upcoming",
      plan: planName(billed.plan),
      amount: money(invoice.amount_due, invoice.currency),
      renewalDate: longDate(renewsAt),
      billingUrl: portalReturnUrl,
    }),
  );
}
