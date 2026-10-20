import type Stripe from "stripe";
import { ValidationError } from "@/shared/errors";
import { logger } from "@/shared/logger";
import {
  classifyPlanChange,
  PLAN_CHANGE_EFFECT,
  type PlanChangeKind,
  type PlanChangeRefusal,
  REFUSAL_MESSAGES,
  resolveTargetPlan,
} from "../service/plan-change";
import {
  customerId,
  expandedLatestInvoice,
  subscriptionPeriodEnd,
  SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
} from "../service/subscription-plan";
import { loadActivePlans, type PlanChangeDeps } from "./current-plan";
import {
  pendingChange,
  releaseSchedule,
  scheduleChange,
  type ScheduledChangeNotice,
} from "./plan-change-schedule";

const applyLogger = logger.child({ module: "plan-change-apply" });

/** A preview older than this no longer describes what Stripe would charge. */
const MAX_PREVIEW_AGE_SECONDS = 60 * 60;
/** Tolerated clock skew between the client's preview and this server. */
const MAX_FUTURE_SKEW_SECONDS = 60;

export type PlanChangeStatus =
  | "ACTIVE"
  | "SCHEDULED"
  | "REQUIRES_ACTION"
  | "FAILED"
  | "REFUSED";

export interface PlanChangeResultView {
  status: PlanChangeStatus;
  kind: PlanChangeKind | null;
  refusal: PlanChangeRefusal | null;
  message: string | null;
  /** Confirm with Stripe.js when `REQUIRES_ACTION`. */
  clientSecret: string | null;
  /** Stripe's hosted page to pay or authenticate the change's invoice. */
  hostedInvoiceUrl: string | null;
  subscriptionId: string | null;
  newTier: string | null;
  currentPeriodEnd: Date | null;
  /** With SCHEDULED: when the new price takes over; nothing is charged now. */
  effectiveAt: Date | null;
  /**
   * With ACTIVE or REQUIRES_ACTION: the invoice the change charges and its
   * amount (minor units), so a client counts the purchase once. Paid with
   * ACTIVE; what the bank is asked to approve with REQUIRES_ACTION.
   */
  invoiceId: string | null;
  amountCharged: number | null;
  currency: string | null;
  /**
   * With SCHEDULED: what was scheduled, for the confirmation email. Not part
   * of the API; the service takes it off before answering.
   */
  scheduledNotice?: ScheduledChangeNotice;
}

export interface PlanChangeApplyOptions {
  /** The previewed proration time, so the charge equals the preview. */
  prorationDate?: number | null;
  /**
   * Refuse end-of-period changes instead of scheduling them, for the legacy
   * `upgradeSubscription` mutation, whose callers expect an immediate change.
   */
  immediateOnly?: boolean;
}

function result(
  status: PlanChangeStatus,
  fields: Partial<Omit<PlanChangeResultView, "status">> = {},
): PlanChangeResultView {
  return {
    status,
    kind: null,
    refusal: null,
    message: null,
    clientSecret: null,
    hostedInvoiceUrl: null,
    subscriptionId: null,
    newTier: null,
    currentPeriodEnd: null,
    effectiveAt: null,
    invoiceId: null,
    amountCharged: null,
    currency: null,
    ...fields,
  };
}

function refused(
  refusal: PlanChangeRefusal,
  fields: Partial<Omit<PlanChangeResultView, "status">> = {},
): PlanChangeResultView {
  return result("REFUSED", {
    refusal,
    message: REFUSAL_MESSAGES[refusal],
    ...fields,
  });
}

/** The PaymentIntent behind an invoice, read from its payment records. */
async function invoicePaymentIntent(
  stripe: Stripe,
  invoice: Stripe.Invoice | null,
): Promise<Stripe.PaymentIntent | null> {
  const payment = invoice?.payments?.data.find(
    (record) => record.payment.type === "payment_intent",
  )?.payment.payment_intent;
  if (!payment) return null;
  return typeof payment === "string"
    ? stripe.paymentIntents.retrieve(payment)
    : payment;
}

/**
 * Apply a plan change. Gains (an upgrade, a switch to yearly) are charged now
 * at the proration time the customer previewed, so the charge equals the
 * preview; losses are scheduled for the end of the paid period.
 *
 * Immediate changes are made with `pending_if_incomplete`: when the payment
 * needs the customer's bank or fails, Stripe keeps the old plan and holds the
 * change as a pending update, so a successful-looking `active` status is not
 * success — the item must actually carry the new price with nothing pending.
 */
export async function applyPlanChange(
  deps: PlanChangeDeps,
  userId: string,
  clientId: string,
  targetPriceId: string,
  { prorationDate, immediateOnly = false }: PlanChangeApplyOptions = {},
): Promise<PlanChangeResultView> {
  const { plans, target } = resolveTargetPlan(clientId, targetPriceId);

  const nowSeconds = Math.floor((deps.now?.() ?? new Date()).getTime() / 1000);
  if (prorationDate != null) {
    if (prorationDate > nowSeconds + MAX_FUTURE_SKEW_SECONDS) {
      throw new ValidationError("prorationDate", "Is in the future");
    }
    if (prorationDate < nowSeconds - MAX_PREVIEW_AGE_SECONDS) {
      throw new ValidationError(
        "prorationDate",
        "The preview expired",
        "Preview the change again",
      );
    }
  }

  const { stripe } = deps;
  const { binding, active } = await loadActivePlans(
    deps,
    userId,
    clientId,
    plans,
  );
  if (active.length > 1) {
    applyLogger.warn("Plan change refused: several active subscriptions", {
      count: active.length,
    });
    return refused("MULTIPLE_SUBSCRIPTIONS");
  }
  const current = active[0];
  if (!current || !binding) return refused("NO_SUBSCRIPTION");
  if (current.subscription.status === "past_due") {
    return refused("PAST_DUE", { subscriptionId: current.subscription.id });
  }

  const classification = classifyPlanChange(current.plan, target);
  if ("refusal" in classification) {
    // A confirm that arrives after its own change landed (a double click or a
    // retried request) finds the target price already in place: report the
    // change as done instead of refusing or charging again.
    if (classification.refusal === "CURRENT_PLAN" && prorationDate != null) {
      return result("ACTIVE", {
        subscriptionId: current.subscription.id,
        newTier: target.tier,
        currentPeriodEnd: new Date(current.item.current_period_end * 1000),
      });
    }
    return refused(classification.refusal, {
      subscriptionId: current.subscription.id,
    });
  }
  const { kind } = classification;
  if (PLAN_CHANGE_EFFECT[kind] === "SCHEDULED") {
    if (immediateOnly) return refused("SCHEDULED_CHANGE", { kind });
    // Losses wait for the end of the paid period, and nothing is charged.
    // Unexpanded, the replaced change is unknown; the email's claim still
    // keeps a repeated confirm to one message.
    const previous =
      typeof current.subscription.schedule === "string"
        ? null
        : pendingChange(current.subscription, plans);
    const { scheduleId, effectiveAt } = await scheduleChange(
      stripe,
      current.subscription,
      current.item,
      target,
    );
    return result("SCHEDULED", {
      kind,
      subscriptionId: current.subscription.id,
      newTier: target.tier,
      currentPeriodEnd: effectiveAt,
      effectiveAt,
      scheduledNotice: {
        subscriptionId: current.subscription.id,
        scheduleId,
        currentPriceId: current.plan.priceId,
        change: { priceId: target.priceId, effectiveAt },
        previous,
      },
    });
  }

  // A pending scheduled change would undo this one at renewal, so it goes
  // first. It cannot wait for the outcome: a payment the bank must approve
  // or that failed leaves Stripe holding the update, which still applies if
  // the invoice is paid later, and an attached schedule would then revert it.
  await releaseSchedule(stripe, current.subscription);
  const proration = prorationDate ?? nowSeconds;
  const updated = await stripe.subscriptions.update(
    current.subscription.id,
    {
      items: [{ id: current.item.id, price: targetPriceId }],
      // A change keeps the subscription, so it withdraws a pending
      // cancellation. Stripe holds the flag in the pending update until the
      // payment succeeds (checked in test mode with declined and
      // bank-approval cards), so a failed change keeps the cancellation. It
      // is always sent, keeping the body stable for the idempotency key.
      cancel_at_period_end: false,
      payment_behavior: "pending_if_incomplete",
      proration_behavior: "always_invoice",
      proration_date: proration,
      expand: ["latest_invoice.payments"],
    },
    {
      idempotencyKey: `plan-change:${current.subscription.id}:${targetPriceId}:${proration}`,
    },
  );
  if (
    !updated.livemode ||
    customerId(updated.customer) !== binding.stripeCustomerId
  ) {
    throw new Error(
      "Updated subscription does not match its live customer binding",
    );
  }

  const applied =
    !updated.pending_update &&
    updated.status === "active" &&
    updated.items.data.some((item) => item.price.id === targetPriceId);
  const invoice = expandedLatestInvoice(updated);
  // A change that made no invoice leaves the previous one latest (a renewal,
  // say), which this change did not charge.
  const changeInvoice =
    invoice?.billing_reason === "subscription_update" ? invoice : null;
  const charge = (amount: "amount_paid" | "amount_due") =>
    changeInvoice?.id
      ? {
          invoiceId: changeInvoice.id,
          amountCharged: changeInvoice[amount],
          currency: changeInvoice.currency,
        }
      : {};
  if (applied) {
    const periodEnd = subscriptionPeriodEnd([{ ...updated, clientId }]);
    if (periodEnd) {
      const recorded = await deps.models.paidCustomer.updatePeriodIfUnchanged(
        deps.db,
        binding,
        periodEnd,
        SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
        target.tier,
      );
      if (!recorded) {
        applyLogger.info("Paid period changed concurrently; left as found", {
          subscriptionId: updated.id,
        });
      }
    }
    return result("ACTIVE", {
      kind,
      subscriptionId: updated.id,
      newTier: target.tier,
      currentPeriodEnd: periodEnd,
      ...charge("amount_paid"),
    });
  }

  const intent = await invoicePaymentIntent(stripe, invoice);
  const hostedInvoiceUrl = invoice?.hosted_invoice_url ?? null;
  if (
    intent &&
    (intent.status === "requires_action" ||
      intent.status === "requires_confirmation")
  ) {
    return result("REQUIRES_ACTION", {
      kind,
      message:
        "Your bank needs to approve this payment. Nothing changes until it does.",
      clientSecret: intent.client_secret,
      hostedInvoiceUrl,
      subscriptionId: updated.id,
      newTier: target.tier,
      ...charge("amount_due"),
    });
  }
  return result("FAILED", {
    kind,
    message:
      "The payment did not go through, so your plan was not changed. Try again or use another card.",
    hostedInvoiceUrl,
    subscriptionId: updated.id,
  });
}
