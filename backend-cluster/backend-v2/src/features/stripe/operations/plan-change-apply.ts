import type Stripe from "stripe";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import { ValidationError } from "@/shared/errors";
import { logger } from "@/shared/logger";
import {
  classifyPlanChange,
  PLAN_CHANGE_EFFECT,
  type PlanChangeKind,
  type PlanChangeRefusal,
} from "../service/plan-change";
import { SUBSCRIPTION_CONFIG } from "../service/stripe";
import {
  customerId,
  subscriptionPeriodEnd,
  SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
} from "../service/subscription-plan";
import { loadActivePlans } from "./current-plan";

const applyLogger = logger.child({ module: "plan-change-apply" });

/** A preview older than this no longer describes what Stripe would charge. */
const MAX_PREVIEW_AGE_SECONDS = 60 * 60;
/** Tolerated clock skew between the client's preview and this server. */
const MAX_FUTURE_SKEW_SECONDS = 60;

export type PlanChangeStatus =
  | "ACTIVE"
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
}

export interface PlanChangeApplyDeps {
  stripe: Stripe;
  models: Pick<IModels, "paidCustomer">;
  db: DbExecutor;
  now?: () => Date;
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
    ...fields,
  };
}

const REFUSAL_MESSAGES: Record<PlanChangeRefusal, string> = {
  CURRENT_PLAN: "You are already on this plan.",
  SAME_TIER_AND_CYCLE:
    "You are already on this plan at your current price; switching would only raise it.",
  MULTIPLE_SUBSCRIPTIONS:
    "Your account has more than one active subscription. Contact support to change plans.",
  NO_SUBSCRIPTION: "You have no subscription to change. Check out instead.",
  SCHEDULED_CHANGE:
    "This change takes effect at the end of your billing period and cannot be applied immediately.",
};

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
 * Apply an immediate plan change (an upgrade or a switch to yearly) at the
 * proration time the customer previewed, so the charge equals the preview.
 *
 * Changes are made with `pending_if_incomplete`: when the payment needs the
 * customer's bank or fails, Stripe keeps the old plan and holds the change as
 * a pending update, so a successful-looking `active` status is not success —
 * the item must actually carry the new price with nothing pending.
 */
export async function applyPlanChange(
  deps: PlanChangeApplyDeps,
  userId: string,
  clientId: string,
  targetPriceId: string,
  prorationDate?: number | null,
): Promise<PlanChangeResultView> {
  const clientConfig = SUBSCRIPTION_CONFIG[clientId];
  if (!clientConfig) throw new ValidationError("clientId", "Unknown client");
  const target = clientConfig.plans.find(
    (plan) => plan.priceId === targetPriceId,
  );
  if (!target) throw new ValidationError("priceId", "Unknown price");

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
    stripe,
    deps.models,
    deps.db,
    userId,
    clientId,
    clientConfig.plans,
  );
  if (active.length > 1) {
    applyLogger.warn("Plan change refused: several active subscriptions", {
      count: active.length,
    });
    return refused("MULTIPLE_SUBSCRIPTIONS");
  }
  const current = active[0];
  if (!current || !binding) return refused("NO_SUBSCRIPTION");

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
  if (PLAN_CHANGE_EFFECT[kind] !== "IMMEDIATE") {
    return refused("SCHEDULED_CHANGE", { kind });
  }

  const proration = prorationDate ?? nowSeconds;
  const updated = await stripe.subscriptions.update(
    current.subscription.id,
    {
      items: [{ id: current.item.id, price: targetPriceId }],
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
  if (applied) {
    const periodEnd = subscriptionPeriodEnd([{ ...updated, clientId }]);
    if (periodEnd) {
      const recorded = await deps.models.paidCustomer.updatePeriodIfUnchanged(
        deps.db,
        binding,
        periodEnd,
        SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
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
    });
  }

  const invoice =
    updated.latest_invoice && typeof updated.latest_invoice === "object"
      ? updated.latest_invoice
      : null;
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
