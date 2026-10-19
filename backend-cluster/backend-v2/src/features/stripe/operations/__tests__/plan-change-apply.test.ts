import Stripe from "stripe";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import { ErrorCategory } from "@/shared/errors";
import { BILLING_CLIENT_ID } from "../../service/stripe";
import { SUBSCRIPTION_PERIOD_VERIFICATION_VERSION } from "../../service/subscription-plan";
import { applyPlanChange } from "../plan-change-apply";

const PREMIUM_MONTHLY = "price_1RrSOGEqsEqs2tLVFnyB34qG";
const PREMIUM_YEARLY = "price_1US5htEqsEqs2tLVENCzLaZB";
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
    schedule: null,
    discounts: [],
    cancel_at_period_end: false,
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

const PERIOD_START = NOW_SECONDS - 86_400 * 20;
const PERIOD_END = NOW_SECONDS + 86_400;
const SCHEDULE = {
  id: "sub_sched_1",
  status: "active",
  current_phase: { start_date: PERIOD_START, end_date: PERIOD_END },
  // Attached by an earlier change, with nothing pending after this period.
  phases: [{ start_date: PERIOD_START, items: [] }],
};

function setup(
  options: {
    subscriptions?: Stripe.Subscription[];
    updated?: Stripe.Subscription;
    intent?: Partial<Stripe.PaymentIntent>;
    immediateOnly?: boolean;
  } = {},
) {
  const stripe = {
    subscriptions: {
      list: jest.fn(async () => ({ data: options.subscriptions ?? [] })),
      update: jest.fn(async () => options.updated),
      retrieve: jest.fn(async () => options.subscriptions?.[0]),
    },
    subscriptionSchedules: {
      create: jest.fn(async () => SCHEDULE),
      retrieve: jest.fn(async () => SCHEDULE),
      update: jest.fn(async () => SCHEDULE),
      release: jest.fn(async () => ({ ...SCHEDULE, status: "released" })),
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
    applyPlanChange(deps, "usr_1", BILLING_CLIENT_ID, priceId, {
      prorationDate,
      immediateOnly: options.immediateOnly,
    });
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
        cancel_at_period_end: false,
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
      "PREMIUM",
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

  it.each([
    ["a downgrade", GROWTH_MONTHLY, PREMIUM_MONTHLY, "DOWNGRADE"],
    ["a switch to monthly", PREMIUM_YEARLY, PREMIUM_MONTHLY, "TO_MONTHLY"],
    ["a higher tier on monthly", PREMIUM_YEARLY, GROWTH_MONTHLY, "SPLIT"],
  ])(
    "schedules %s for the period end with nothing charged",
    async (_label, from, to, kind) => {
      const { stripe, apply } = setup({
        subscriptions: [subscription(from, { discounts: ["di_forever"] })],
      });

      await expect(apply(to, NOW_SECONDS)).resolves.toMatchObject({
        status: "SCHEDULED",
        kind,
        effectiveAt: new Date(PERIOD_END * 1000),
      });
      expect(stripe.subscriptionSchedules.create).toHaveBeenCalledWith({
        from_subscription: "sub_1",
      });
      expect(stripe.subscriptionSchedules.update).toHaveBeenCalledWith(
        "sub_sched_1",
        {
          end_behavior: "release",
          proration_behavior: "none",
          phases: [
            {
              items: [{ price: from, quantity: 1 }],
              start_date: PERIOD_START,
              end_date: PERIOD_END,
              discounts: [{ discount: "di_forever" }],
            },
            {
              items: [{ price: to, quantity: 1 }],
              duration: { interval: "month", interval_count: 1 },
              discounts: [{ discount: "di_forever" }],
              proration_behavior: "none",
            },
          ],
        },
      );
      // Nothing is charged or changed on the subscription itself.
      expect(stripe.subscriptions.update).not.toHaveBeenCalled();
    },
  );

  it("replaces the next phase of a schedule already attached", async () => {
    const { stripe, apply } = setup({
      subscriptions: [
        subscription(GROWTH_MONTHLY, { schedule: "sub_sched_1" }),
      ],
    });

    await apply(PREMIUM_MONTHLY, NOW_SECONDS);

    expect(stripe.subscriptionSchedules.create).not.toHaveBeenCalled();
    expect(stripe.subscriptionSchedules.retrieve).toHaveBeenCalledWith(
      "sub_sched_1",
    );
    expect(stripe.subscriptionSchedules.update).toHaveBeenCalledTimes(1);
  });

  it("uses the schedule a concurrent confirm attached first", async () => {
    const { stripe, apply } = setup({
      subscriptions: [subscription(GROWTH_MONTHLY)],
    });
    stripe.subscriptionSchedules.create.mockRejectedValueOnce(
      new Stripe.errors.StripeInvalidRequestError({
        type: "invalid_request_error",
        message: "The subscription is already attached to a schedule.",
      }),
    );
    stripe.subscriptions.retrieve.mockResolvedValueOnce(
      subscription(GROWTH_MONTHLY, { schedule: "sub_sched_1" }),
    );

    await expect(apply(PREMIUM_MONTHLY, NOW_SECONDS)).resolves.toMatchObject({
      status: "SCHEDULED",
    });
    expect(stripe.subscriptionSchedules.update).toHaveBeenCalledTimes(1);
  });

  it("does not mistake a network failure for a race", async () => {
    const { stripe, apply } = setup({
      subscriptions: [subscription(GROWTH_MONTHLY)],
    });
    stripe.subscriptionSchedules.create.mockRejectedValueOnce(
      new Stripe.errors.StripeConnectionError({
        type: "api_error",
        message: "socket hang up",
      }),
    );

    await expect(apply(PREMIUM_MONTHLY, NOW_SECONDS)).rejects.toThrow(
      "socket hang up",
    );
    expect(stripe.subscriptions.retrieve).not.toHaveBeenCalled();
    expect(stripe.subscriptionSchedules.update).not.toHaveBeenCalled();
  });

  it("keeps every other item and its quantity in both phases", async () => {
    const { stripe, apply } = setup({
      subscriptions: [
        subscription(GROWTH_MONTHLY, {
          items: {
            data: [
              {
                id: "si_1",
                price: { id: GROWTH_MONTHLY },
                quantity: 1,
                current_period_end: PERIOD_END,
              },
              {
                id: "si_addon",
                price: { id: "price_addon" },
                quantity: 3,
                current_period_end: PERIOD_END,
              },
            ],
          },
        }),
      ],
    });

    await apply(PREMIUM_MONTHLY, NOW_SECONDS);

    const [, params] = stripe.subscriptionSchedules.update.mock
      .calls[0] as unknown as [string, Stripe.SubscriptionScheduleUpdateParams];
    expect(params.phases?.map((phase) => phase.items)).toEqual([
      [
        { price: GROWTH_MONTHLY, quantity: 1 },
        { price: "price_addon", quantity: 3 },
      ],
      [
        { price: PREMIUM_MONTHLY, quantity: 1 },
        { price: "price_addon", quantity: 3 },
      ],
    ]);
  });

  it("uses an expanded schedule as is, and ends its current phase at the period end", async () => {
    const { stripe, apply } = setup({
      subscriptions: [
        subscription(GROWTH_MONTHLY, {
          schedule: {
            ...SCHEDULE,
            current_phase: { start_date: PERIOD_START, end_date: 1 },
          },
        }),
      ],
    });

    await expect(apply(PREMIUM_MONTHLY, NOW_SECONDS)).resolves.toMatchObject({
      effectiveAt: new Date(PERIOD_END * 1000),
    });
    expect(stripe.subscriptionSchedules.retrieve).not.toHaveBeenCalled();
    const [, params] = stripe.subscriptionSchedules.update.mock
      .calls[0] as unknown as [string, Stripe.SubscriptionScheduleUpdateParams];
    expect(params.phases?.[0]).toMatchObject({
      start_date: PERIOD_START,
      end_date: PERIOD_END,
    });
  });

  it("releases a pending scheduled change before an immediate one, so renewal cannot undo it", async () => {
    const { stripe, apply } = setup({
      subscriptions: [
        subscription(PREMIUM_MONTHLY, { schedule: "sub_sched_1" }),
      ],
      updated: subscription(PREMIUM_YEARLY),
    });

    await apply(PREMIUM_YEARLY, NOW_SECONDS);

    expect(stripe.subscriptionSchedules.release).toHaveBeenCalledWith(
      "sub_sched_1",
    );
    expect(
      stripe.subscriptionSchedules.release.mock.invocationCallOrder[0],
    ).toBeLessThan(stripe.subscriptions.update.mock.invocationCallOrder[0]);
  });

  it("withdraws a pending cancellation in the same update as an immediate change, which Stripe holds until the payment succeeds", async () => {
    const { stripe, apply } = setup({
      subscriptions: [
        subscription(PREMIUM_MONTHLY, { cancel_at_period_end: true }),
      ],
      updated: subscription(PREMIUM_YEARLY),
    });

    await apply(PREMIUM_YEARLY, NOW_SECONDS);

    expect(stripe.subscriptions.update).toHaveBeenCalledTimes(1);
    expect(stripe.subscriptions.update).toHaveBeenCalledWith(
      "sub_1",
      expect.objectContaining({
        items: [{ id: "si_1", price: PREMIUM_YEARLY }],
        cancel_at_period_end: false,
        payment_behavior: "pending_if_incomplete",
      }),
      expect.anything(),
    );
  });

  it("refuses any change while a renewal is past due, with no Stripe write", async () => {
    const { stripe, apply } = setup({
      subscriptions: [
        subscription(PREMIUM_MONTHLY, {
          status: "past_due",
          latest_invoice: { status: "open", next_payment_attempt: PERIOD_END },
        }),
      ],
    });

    await expect(apply(GROWTH_MONTHLY, NOW_SECONDS)).resolves.toMatchObject({
      status: "REFUSED",
      refusal: "PAST_DUE",
    });
    expect(stripe.subscriptions.update).not.toHaveBeenCalled();
    expect(stripe.subscriptionSchedules.create).not.toHaveBeenCalled();
  });

  it.each([
    ["$9.99 monthly", "price_1L9ccEEqsEqs2tLVKPRV17wb"],
    ["$99.99 yearly", "price_1L9ccEEqsEqs2tLVbeBgHm9p"],
  ])(
    "refuses the retired %s Premium price as a target before any Stripe call",
    async (_label, retired) => {
      const { stripe, apply } = setup({
        subscriptions: [subscription(GROWTH_MONTHLY)],
      });

      await expect(apply(retired, NOW_SECONDS)).rejects.toMatchObject({
        category: ErrorCategory.VALIDATION_FAILED,
      });
      expect(stripe.subscriptions.list).not.toHaveBeenCalled();
    },
  );

  it.each([
    // A lower tier, on the same cycle.
    ["DOWNGRADE", GROWTH_MONTHLY, PREMIUM_MONTHLY],
    // Yearly to monthly on the same tier.
    ["TO_MONTHLY", PREMIUM_YEARLY, PREMIUM_MONTHLY],
    // A higher tier while leaving yearly.
    ["SPLIT", PREMIUM_YEARLY, GROWTH_MONTHLY],
  ])(
    "refuses an end-of-period %s for the immediate-only legacy mutation, with no Stripe write",
    async (kind, currentPriceId, targetPriceId) => {
      const { stripe, apply } = setup({
        subscriptions: [subscription(currentPriceId)],
        immediateOnly: true,
      });

      await expect(apply(targetPriceId, NOW_SECONDS)).resolves.toMatchObject({
        status: "REFUSED",
        refusal: "SCHEDULED_CHANGE",
        kind,
      });
      expect(stripe.subscriptions.update).not.toHaveBeenCalled();
      expect(stripe.subscriptionSchedules.create).not.toHaveBeenCalled();
      expect(stripe.subscriptionSchedules.update).not.toHaveBeenCalled();
      expect(stripe.subscriptionSchedules.release).not.toHaveBeenCalled();
    },
  );

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
  ])(
    "rejects a proration time %s before reading billing state",
    async (_name, when) => {
      const { stripe, apply } = setup({
        subscriptions: [subscription(PREMIUM_MONTHLY)],
      });

      await expect(apply(PREMIUM_YEARLY, when)).rejects.toMatchObject({
        category: ErrorCategory.VALIDATION_FAILED,
      });
      expect(stripe.subscriptions.list).not.toHaveBeenCalled();
    },
  );
});
