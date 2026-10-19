import type Stripe from "stripe";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import { ErrorCategory } from "@/shared/errors";
import { BILLING_CLIENT_ID } from "../../service/stripe";
import { previewPlanChange } from "../plan-change-preview";

const LEGACY_PREMIUM_MONTHLY = "price_1L9ccEEqsEqs2tLVKPRV17wb";
const PREMIUM_MONTHLY = "price_1RrSOGEqsEqs2tLVFnyB34qG";
const PREMIUM_YEARLY = "price_1L9ccEEqsEqs2tLVbeBgHm9p";
const GROWTH_MONTHLY = "price_1SyPdaEqsEqs2tLViLPUDoVi";
const GROWTH_YEARLY = "price_1SyPdbEqsEqs2tLV7PJyWZed";

const LIST_PRICES: Record<string, number> = {
  [LEGACY_PREMIUM_MONTHLY]: 999,
  [PREMIUM_MONTHLY]: 1499,
  [PREMIUM_YEARLY]: 9999,
  [GROWTH_MONTHLY]: 9999,
  [GROWTH_YEARLY]: 95988,
};

const NOW = new Date("2026-10-17T12:00:00Z");
const NOW_SECONDS = Math.floor(NOW.getTime() / 1000);
const PERIOD_END = new Date("2026-11-03T12:00:00Z");

function subscription(
  priceId: string,
  overrides: Partial<Record<string, unknown>> = {},
): Stripe.Subscription {
  return {
    id: "sub_1",
    customer: "cus_1",
    livemode: true,
    status: "active",
    cancel_at_period_end: false,
    default_payment_method: "pm_1",
    items: {
      data: [
        {
          id: "si_1",
          price: { id: priceId },
          current_period_end: Math.floor(PERIOD_END.getTime() / 1000),
        },
      ],
    },
    ...overrides,
  } as unknown as Stripe.Subscription;
}

function setup(
  options: {
    binding?: boolean;
    subscriptions?: Stripe.Subscription[];
    invoice?: Partial<Stripe.Invoice>;
  } = {},
) {
  const stripe = {
    subscriptions: {
      list: jest.fn(async () => ({ data: options.subscriptions ?? [] })),
    },
    prices: {
      retrieve: jest.fn(async (id: string) => ({
        id,
        unit_amount: LIST_PRICES[id],
        currency: "usd",
      })),
    },
    invoices: {
      createPreview: jest.fn(async () => ({
        amount_due: 0,
        currency: "usd",
        lines: { data: [] },
        ...options.invoice,
      })),
    },
    paymentMethods: {
      retrieve: jest.fn(async () => ({
        card: { brand: "visa", last4: "4242" },
      })),
    },
    customers: {
      retrieve: jest.fn(async () => ({
        deleted: false,
        invoice_settings: {
          default_payment_method: {
            card: { brand: "mastercard", last4: "4444" },
          },
        },
      })),
    },
  };
  const findByUserIdAndClientId = jest.fn(async () =>
    options.binding === false
      ? null
      : {
          userId: "usr_1",
          clientId: BILLING_CLIENT_ID,
          stripeCustomerId: "cus_1",
        },
  );
  const deps = {
    stripe: stripe as unknown as Stripe,
    models: {
      paidCustomer: { findByUserIdAndClientId },
    } as unknown as Pick<IModels, "paidCustomer">,
    db: {} as DbExecutor,
    now: () => NOW,
  };
  const preview = (priceId: string) =>
    previewPlanChange(deps, "usr_1", BILLING_CLIENT_ID, priceId);
  return { stripe, preview };
}

describe("previewPlanChange", () => {
  it("sends a customer without a subscription to Checkout at the list price", async () => {
    const { stripe, preview } = setup({ binding: false });

    const result = await preview(PREMIUM_YEARLY);

    expect(result).toMatchObject({
      kind: "NEW",
      effect: "CHECKOUT",
      refusal: null,
      currentPriceId: null,
      amountDueToday: 9999,
      nextAmount: 9999,
      nextChargeAt: new Date("2027-10-17T12:00:00Z"),
    });
    expect(result.limitChanges).toContainEqual({
      limit: "maxLedgers",
      from: 1,
      to: 5,
    });
    expect(stripe.subscriptions.list).not.toHaveBeenCalled();
    expect(stripe.invoices.createPreview).not.toHaveBeenCalled();
  });

  it("asks Stripe what a switch to yearly charges, at a fixed proration time", async () => {
    const { stripe, preview } = setup({
      subscriptions: [subscription(PREMIUM_MONTHLY)],
      invoice: {
        amount_due: 9000,
        lines: {
          data: [{ amount: -999 }, { amount: 9999 }],
        } as unknown as Stripe.Invoice["lines"],
      },
    });

    const result = await preview(PREMIUM_YEARLY);

    expect(stripe.invoices.createPreview).toHaveBeenCalledWith({
      customer: "cus_1",
      subscription: "sub_1",
      subscription_details: {
        items: [{ id: "si_1", price: PREMIUM_YEARLY }],
        proration_behavior: "always_invoice",
        proration_date: NOW_SECONDS,
      },
    });
    expect(result).toMatchObject({
      kind: "TO_YEARLY",
      effect: "IMMEDIATE",
      currentPriceId: PREMIUM_MONTHLY,
      amountDueToday: 9000,
      creditApplied: 999,
      nextAmount: 9999,
      prorationDate: NOW_SECONDS,
      effectiveAt: NOW,
      // A new yearly cycle starts at the switch.
      nextChargeAt: new Date("2027-10-17T12:00:00Z"),
      paymentMethod: { brand: "visa", last4: "4242" },
    });
    expect(stripe.paymentMethods.retrieve).toHaveBeenCalledWith("pm_1");
  });

  it("keeps the renewal date for an upgrade on the same cycle", async () => {
    const { preview } = setup({
      subscriptions: [subscription(PREMIUM_MONTHLY)],
      invoice: { amount_due: 4250 },
    });

    const result = await preview(GROWTH_MONTHLY);

    expect(result).toMatchObject({
      kind: "UPGRADE",
      effect: "IMMEDIATE",
      amountDueToday: 4250,
      nextChargeAt: PERIOD_END,
    });
  });

  it("schedules a downgrade for the end of the paid period without asking Stripe to price it", async () => {
    const { stripe, preview } = setup({
      subscriptions: [subscription(GROWTH_YEARLY)],
    });

    const result = await preview(PREMIUM_YEARLY);

    expect(result).toMatchObject({
      kind: "DOWNGRADE",
      effect: "SCHEDULED",
      amountDueToday: 0,
      effectiveAt: PERIOD_END,
      nextChargeAt: PERIOD_END,
      prorationDate: null,
    });
    expect(result.limitChanges).toContainEqual({
      limit: "maxLedgers",
      from: 20,
      to: 5,
    });
    expect(stripe.invoices.createPreview).not.toHaveBeenCalled();
  });

  it("offers the higher tier on the current cycle when a change would leave yearly", async () => {
    const { preview } = setup({
      subscriptions: [subscription(PREMIUM_YEARLY)],
    });

    const result = await preview(GROWTH_MONTHLY);

    expect(result).toMatchObject({
      kind: "SPLIT",
      effect: "SCHEDULED",
      alternativePriceId: GROWTH_YEARLY,
    });
  });

  it("refuses moving a legacy price to today's price on the same tier and cycle", async () => {
    const { stripe, preview } = setup({
      subscriptions: [subscription(LEGACY_PREMIUM_MONTHLY)],
    });

    const result = await preview(PREMIUM_MONTHLY);

    expect(result).toMatchObject({
      kind: null,
      effect: null,
      refusal: "SAME_TIER_AND_CYCLE",
      currentPriceId: LEGACY_PREMIUM_MONTHLY,
    });
    expect(stripe.invoices.createPreview).not.toHaveBeenCalled();
    expect(stripe.paymentMethods.retrieve).not.toHaveBeenCalled();
  });

  it("refuses the price already held", async () => {
    const { preview } = setup({
      subscriptions: [subscription(PREMIUM_MONTHLY)],
    });

    await expect(preview(PREMIUM_MONTHLY)).resolves.toMatchObject({
      refusal: "CURRENT_PLAN",
    });
  });

  it("refuses to guess between two active paid subscriptions", async () => {
    const { stripe, preview } = setup({
      subscriptions: [
        subscription(PREMIUM_MONTHLY),
        subscription(GROWTH_MONTHLY, { id: "sub_2" }),
      ],
    });

    const result = await preview(GROWTH_YEARLY);

    expect(result).toMatchObject({
      kind: null,
      refusal: "MULTIPLE_SUBSCRIPTIONS",
    });
    expect(stripe.invoices.createPreview).not.toHaveBeenCalled();
  });

  it("ignores test-mode and foreign-customer subscriptions", async () => {
    const { preview } = setup({
      subscriptions: [
        subscription(PREMIUM_MONTHLY, { livemode: false }),
        subscription(GROWTH_MONTHLY, { customer: "cus_other" }),
      ],
    });

    await expect(preview(PREMIUM_YEARLY)).resolves.toMatchObject({
      kind: "NEW",
    });
  });

  it("falls back to the customer's invoice default card", async () => {
    const { stripe, preview } = setup({
      subscriptions: [
        subscription(PREMIUM_MONTHLY, { default_payment_method: null }),
      ],
    });

    const result = await preview(PREMIUM_YEARLY);

    expect(result.paymentMethod).toEqual({
      brand: "mastercard",
      last4: "4444",
    });
    expect(stripe.customers.retrieve).toHaveBeenCalledWith("cus_1", {
      expand: ["invoice_settings.default_payment_method"],
    });
  });

  it("rejects a price outside the configured catalog", async () => {
    const { stripe, preview } = setup();

    await expect(preview("price_unknown")).rejects.toMatchObject({
      category: ErrorCategory.VALIDATION_FAILED,
    });
    expect(stripe.subscriptions.list).not.toHaveBeenCalled();
  });

  it("refuses to preview a change while a renewal is past due", async () => {
    const { stripe, preview } = setup({
      subscriptions: [
        subscription(PREMIUM_MONTHLY, {
          status: "past_due",
          latest_invoice: {
            status: "open",
            next_payment_attempt: NOW_SECONDS + 86_400,
          },
        }),
      ],
    });

    await expect(preview(GROWTH_MONTHLY)).resolves.toMatchObject({
      kind: null,
      refusal: "PAST_DUE",
    });
    expect(stripe.invoices.createPreview).not.toHaveBeenCalled();
  });

  describe("one pending change at a time", () => {
    const PERIOD_END_SECONDS = Math.floor(PERIOD_END.getTime() / 1000);
    const pendingDowngrade = {
      id: "sub_sched_1",
      status: "active",
      current_phase: {
        start_date: NOW_SECONDS - 86_400,
        end_date: PERIOD_END_SECONDS,
      },
      phases: [
        {
          start_date: NOW_SECONDS - 86_400,
          items: [{ price: GROWTH_MONTHLY }],
        },
        { start_date: PERIOD_END_SECONDS, items: [{ price: PREMIUM_MONTHLY }] },
      ],
    };

    it("says which scheduled change a different choice replaces", async () => {
      const { preview } = setup({
        subscriptions: [
          subscription(GROWTH_MONTHLY, { schedule: pendingDowngrade }),
        ],
      });

      await expect(preview(GROWTH_YEARLY)).resolves.toMatchObject({
        kind: "TO_YEARLY",
        replacesScheduledChange: {
          priceId: PREMIUM_MONTHLY,
          effectiveAt: PERIOD_END,
        },
        withdrawsCancellation: false,
      });
    });

    it("replaces nothing when the choice is the change already scheduled", async () => {
      const { preview } = setup({
        subscriptions: [
          subscription(GROWTH_MONTHLY, { schedule: pendingDowngrade }),
        ],
      });

      await expect(preview(PREMIUM_MONTHLY)).resolves.toMatchObject({
        kind: "DOWNGRADE",
        replacesScheduledChange: null,
      });
    });

    it("says a change withdraws a pending cancellation", async () => {
      const { preview } = setup({
        subscriptions: [
          subscription(GROWTH_MONTHLY, { cancel_at_period_end: true }),
        ],
      });

      await expect(preview(PREMIUM_MONTHLY)).resolves.toMatchObject({
        kind: "DOWNGRADE",
        withdrawsCancellation: true,
        replacesScheduledChange: null,
      });
    });

    it("withdraws and replaces nothing for a refused choice", async () => {
      const { preview } = setup({
        subscriptions: [
          subscription(GROWTH_MONTHLY, {
            cancel_at_period_end: true,
            schedule: pendingDowngrade,
          }),
        ],
      });

      await expect(preview(GROWTH_MONTHLY)).resolves.toMatchObject({
        refusal: "CURRENT_PLAN",
        withdrawsCancellation: false,
        replacesScheduledChange: null,
      });
    });
  });
});
