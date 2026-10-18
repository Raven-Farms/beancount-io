import type Stripe from "stripe";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import { ErrorCategory } from "@/shared/errors";
import { BILLING_CLIENT_ID } from "../../service/stripe";
import { SUBSCRIPTION_PERIOD_VERIFICATION_VERSION } from "../../service/subscription-plan";
import { applyPlanChange } from "../plan-change-apply";

const PREMIUM_MONTHLY = "price_1RrSOGEqsEqs2tLVFnyB34qG";
const PREMIUM_YEARLY = "price_1L9ccEEqsEqs2tLVbeBgHm9p";
const GROWTH_MONTHLY = "price_1SyPdaEqsEqs2tLViLPUDoVi";

const NOW = new Date("2026-10-17T12:00:00Z");
const NOW_SECONDS = Math.floor(NOW.getTime() / 1000);
const NEW_PERIOD_END = Math.floor(
  new Date("2027-10-17T12:00:00Z").getTime() / 1000,
);
const BINDING = {
  id: "pc_1",
  userId: "usr_1",
  clientId: BILLING_CLIENT_ID,
  stripeCustomerId: "cus_1",
};

function subscription(
  priceId: string,
  overrides: Record<string, unknown> = {},
): Stripe.Subscription {
  return {
    id: "sub_1",
    customer: "cus_1",
    livemode: true,
    status: "active",
    pending_update: null,
    clientId: BILLING_CLIENT_ID,
    items: {
      data: [
        {
          id: "si_1",
          price: { id: priceId },
          current_period_end: NOW_SECONDS + 86_400,
        },
      ],
    },
    ...overrides,
  } as unknown as Stripe.Subscription;
}

function setup(
  options: {
    subscriptions?: Stripe.Subscription[];
    updated?: Stripe.Subscription;
    intent?: Partial<Stripe.PaymentIntent>;
  } = {},
) {
  const stripe = {
    subscriptions: {
      list: jest.fn(async () => ({ data: options.subscriptions ?? [] })),
      update: jest.fn(async () => options.updated),
    },
    paymentIntents: {
      retrieve: jest.fn(async () => options.intent),
    },
  };
  const paidCustomer = {
    findByUserIdAndClientId: jest.fn(async () => BINDING),
    updatePeriodIfUnchanged: jest.fn(async () => true),
  };
  const deps = {
    stripe: stripe as unknown as Stripe,
    models: { paidCustomer } as unknown as Pick<IModels, "paidCustomer">,
    db: {} as DbExecutor,
    now: () => NOW,
  };
  const apply = (priceId: string, prorationDate?: number | null) =>
    applyPlanChange(deps, "usr_1", BILLING_CLIENT_ID, priceId, prorationDate);
  return { stripe, paidCustomer, apply };
}

/** The invoice a pending update left open, with its one payment record. */
function pendingUpdate(priceId: string): Stripe.Subscription {
  return subscription(priceId, {
    pending_update: { subscription_items: [{ price: { id: PREMIUM_YEARLY } }] },
    latest_invoice: {
      id: "in_1",
      hosted_invoice_url: "https://invoice.stripe.com/i/in_1",
      payments: {
        data: [{ payment: { type: "payment_intent", payment_intent: "pi_1" } }],
      },
    },
  });
}

describe("applyPlanChange", () => {
  it("charges at the previewed proration time, once, and records the new period as verified", async () => {
    const { stripe, paidCustomer, apply } = setup({
      subscriptions: [subscription(PREMIUM_MONTHLY)],
      updated: subscription(PREMIUM_YEARLY, {
        items: {
          data: [
            {
              id: "si_1",
              price: { id: PREMIUM_YEARLY },
              current_period_end: NEW_PERIOD_END,
            },
          ],
        },
      }),
    });

    const result = await apply(PREMIUM_YEARLY, NOW_SECONDS - 30);

    expect(stripe.subscriptions.update).toHaveBeenCalledWith(
      "sub_1",
      {
        items: [{ id: "si_1", price: PREMIUM_YEARLY }],
        payment_behavior: "pending_if_incomplete",
        proration_behavior: "always_invoice",
        proration_date: NOW_SECONDS - 30,
        expand: ["latest_invoice.payments"],
      },
      {
        idempotencyKey: `plan-change:sub_1:${PREMIUM_YEARLY}:${NOW_SECONDS - 30}`,
      },
    );
    expect(result).toMatchObject({
      status: "ACTIVE",
      kind: "TO_YEARLY",
      newTier: "PREMIUM",
      currentPeriodEnd: new Date(NEW_PERIOD_END * 1000),
    });
    expect(paidCustomer.updatePeriodIfUnchanged).toHaveBeenCalledWith(
      {},
      BINDING,
      new Date(NEW_PERIOD_END * 1000),
      SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
    );
  });

  it("reports a change waiting on the customer's bank instead of calling it done or failed", async () => {
    const { paidCustomer, apply } = setup({
      subscriptions: [subscription(PREMIUM_MONTHLY)],
      // Stripe keeps the old price active while the update is pending.
      updated: pendingUpdate(PREMIUM_MONTHLY),
      intent: { status: "requires_action", client_secret: "pi_1_secret" },
    });

    const result = await apply(PREMIUM_YEARLY, NOW_SECONDS);

    expect(result).toMatchObject({
      status: "REQUIRES_ACTION",
      clientSecret: "pi_1_secret",
      hostedInvoiceUrl: "https://invoice.stripe.com/i/in_1",
    });
    expect(paidCustomer.updatePeriodIfUnchanged).not.toHaveBeenCalled();
  });

  it("reports a declined payment as failed with nothing changed", async () => {
    const { paidCustomer, apply } = setup({
      subscriptions: [subscription(PREMIUM_MONTHLY)],
      updated: pendingUpdate(PREMIUM_MONTHLY),
      intent: { status: "requires_payment_method", client_secret: "x" },
    });

    const result = await apply(PREMIUM_YEARLY, NOW_SECONDS);

    expect(result).toMatchObject({ status: "FAILED", clientSecret: null });
    expect(paidCustomer.updatePeriodIfUnchanged).not.toHaveBeenCalled();
  });

  it("treats a replayed confirm whose change already landed as done, without a second charge", async () => {
    const { stripe, apply } = setup({
      subscriptions: [subscription(PREMIUM_YEARLY)],
    });

    const result = await apply(PREMIUM_YEARLY, NOW_SECONDS);

    expect(result).toMatchObject({ status: "ACTIVE", newTier: "PREMIUM" });
    expect(stripe.subscriptions.update).not.toHaveBeenCalled();
  });

  it("refuses the current plan when no preview is being confirmed", async () => {
    const { stripe, apply } = setup({
      subscriptions: [subscription(PREMIUM_MONTHLY)],
    });

    await expect(apply(PREMIUM_MONTHLY)).resolves.toMatchObject({
      status: "REFUSED",
      refusal: "CURRENT_PLAN",
    });
    expect(stripe.subscriptions.update).not.toHaveBeenCalled();
  });

  it("refuses a change that waits for the period end, with no Stripe write", async () => {
    const { stripe, apply } = setup({
      subscriptions: [subscription(GROWTH_MONTHLY)],
    });

    await expect(apply(PREMIUM_MONTHLY, NOW_SECONDS)).resolves.toMatchObject({
      status: "REFUSED",
      refusal: "SCHEDULED_CHANGE",
      kind: "DOWNGRADE",
    });
    expect(stripe.subscriptions.update).not.toHaveBeenCalled();
  });

  it("sends a customer without a subscription to Checkout", async () => {
    const { apply } = setup({ subscriptions: [] });

    await expect(apply(PREMIUM_YEARLY)).resolves.toMatchObject({
      status: "REFUSED",
      refusal: "NO_SUBSCRIPTION",
    });
  });

  it("refuses to choose between two active paid subscriptions", async () => {
    const { stripe, apply } = setup({
      subscriptions: [
        subscription(PREMIUM_MONTHLY),
        subscription(GROWTH_MONTHLY, { id: "sub_2" }),
      ],
    });

    await expect(apply(PREMIUM_YEARLY, NOW_SECONDS)).resolves.toMatchObject({
      status: "REFUSED",
      refusal: "MULTIPLE_SUBSCRIPTIONS",
    });
    expect(stripe.subscriptions.update).not.toHaveBeenCalled();
  });

  it.each([
    ["from the future", NOW_SECONDS + 3_600],
    ["older than an hour", NOW_SECONDS - 7_200],
  ])("rejects a proration time %s before reading billing state", async (_name, when) => {
    const { stripe, apply } = setup({
      subscriptions: [subscription(PREMIUM_MONTHLY)],
    });

    await expect(apply(PREMIUM_YEARLY, when)).rejects.toMatchObject({
      category: ErrorCategory.VALIDATION_FAILED,
    });
    expect(stripe.subscriptions.list).not.toHaveBeenCalled();
  });
});
