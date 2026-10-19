import "reflect-metadata";
import Router from "@koa/router";
import { setStripeWebhookHandler } from "../stripe-webhook-handler";
import { BILLING_CLIENT_ID } from "../../service/stripe";
import { SUBSCRIPTION_PERIOD_VERIFICATION_VERSION } from "../../service/subscription-plan";
import type { AppLayers } from "@/foundation/composition";

jest.mock("@/features/stripe/service/stripe", () => {
  const actual = jest.requireActual("@/features/stripe/service/stripe");
  return {
    ...actual,
    SUBSCRIPTION_CONFIG: {
      "beancount-web-prod": {
        ...actual.SUBSCRIPTION_CONFIG["beancount-web-prod"],
        webhookSecret: "whsec_synthetic",
      },
    },
  };
});
jest.mock("@/server/rest/openapi-registry", () => ({
  registerRoute: jest.fn(),
}));
const mockReportPurchase = jest.fn(async () => "reported");
jest.mock("../../operations/report-purchase", () => ({
  ...jest.requireActual("../../operations/report-purchase"),
  reportPurchase: (...args: unknown[]) => mockReportPurchase(...(args as [])),
}));

const ANALYTICS = {
  gaMeasurementId: "G-SYNTHETIC",
  measurementProtocolSecret: "mp_secret_synthetic",
};

function setup(event: any) {
  const constructEvent = jest.fn(() => event);
  const stripe = {
    getStripeInstance: jest.fn(() => ({ webhooks: { constructEvent } })),
    handleCustomerEvent: jest.fn(),
    handleCheckoutSessionCompleted: jest.fn(),
    listSubscriptions: jest.fn(async () => []),
  };
  const paidCustomer = {
    findByStripeCustomerIdAndClientId: jest.fn(async () => ({
      userId: "usr_synthetic",
    })),
    findByUserId: jest.fn(async () => []),
    updatePeriodIfUnchanged: jest.fn(),
  };
  const router = new Router();
  setStripeWebhookHandler(
    router,
    {
      services: { stripe },
      database: { db: {}, models: { paidCustomer } },
    } as unknown as AppLayers,
    ANALYTICS,
  );
  const handler = router.stack.find((layer) => layer.methods.includes("POST"))!
    .stack[0];
  const ctx: any = {
    request: {
      headers: { "stripe-signature": "sig_synthetic" },
      rawBody: "raw signed payload",
    },
  };
  return {
    stripe,
    paidCustomer,
    constructEvent,
    ctx,
    run: () => handler(ctx, async () => {}),
  };
}
const subscriptionEvent = (overrides = {}) => ({
  id: "evt_synthetic",
  livemode: true,
  type: "customer.subscription.updated",
  data: { object: { customer: "cus_synthetic", metadata: {} } },
  ...overrides,
});

describe("live Stripe webhook boundary", () => {
  it("revalidates and clears a historical period on a verified live webhook", async () => {
    const t = setup(subscriptionEvent());
    const binding = {
      id: "binding_synthetic",
      userId: "usr_synthetic",
      clientId: BILLING_CLIENT_ID,
      stripeCustomerId: "cus_synthetic",
      currentPeriodEnd: new Date(2100000000000),
    };
    t.paidCustomer.findByUserId.mockResolvedValue([binding] as never);
    await t.run();
    expect(t.paidCustomer.updatePeriodIfUnchanged).toHaveBeenCalledWith(
      {},
      binding,
      null,
      SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
    );
    expect(t.ctx.body.processed).toBe(true);
  });
  it("verifies with the configured live secret before consulting metadata", async () => {
    const t = setup(subscriptionEvent());
    await t.run();
    expect(t.constructEvent).toHaveBeenCalledWith(
      "raw signed payload",
      "sig_synthetic",
      "whsec_synthetic",
    );
    expect(
      t.paidCustomer.findByStripeCustomerIdAndClientId,
    ).toHaveBeenCalledWith({}, "cus_synthetic", BILLING_CLIENT_ID);
    // Webhooks refresh periods only; they never pay to expand schedules.
    expect(t.stripe.listSubscriptions).toHaveBeenCalledWith("usr_synthetic", {
      bindings: [],
      status: "active",
      expandSchedule: false,
    });
    expect(t.ctx.body.processed).toBe(true);
  });
  it.each([
    subscriptionEvent({ livemode: false }),
    subscriptionEvent({
      data: { object: { metadata: { clientId: "beancount-web-dev" } } },
    }),
  ])(
    "acknowledges retired/test events without any billing work",
    async (event) => {
      const t = setup(event);
      await t.run();
      expect(t.ctx.status).toBe(200);
      expect(t.ctx.body.processed).toBe(false);
      expect(
        t.paidCustomer.findByStripeCustomerIdAndClientId,
      ).not.toHaveBeenCalled();
      expect(t.stripe.listSubscriptions).not.toHaveBeenCalled();
    },
  );
  it.each([
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
  ])(
    "re-reads current state for %s rather than copying the event period",
    async (type) => {
      const t = setup(subscriptionEvent({ type }));
      await t.run();
      expect(t.stripe.listSubscriptions).toHaveBeenCalledTimes(1);
      expect(t.paidCustomer.updatePeriodIfUnchanged).not.toHaveBeenCalled();
    },
  );
  it("ignores a mismatched user without updating another binding", async () => {
    const t = setup(
      subscriptionEvent({
        data: {
          object: {
            customer: "cus_synthetic",
            metadata: { userId: "usr_other" },
          },
        },
      }),
    );
    await t.run();
    expect(t.stripe.listSubscriptions).not.toHaveBeenCalled();
    expect(t.ctx.body.processed).toBe(false);
  });
  it("does no work on invalid signatures or missing input", async () => {
    const t = setup(subscriptionEvent());
    t.constructEvent.mockImplementation(() => {
      throw new Error("invalid signature");
    });
    await t.run();
    expect(t.ctx.status).toBe(400);
    expect(t.stripe.listSubscriptions).not.toHaveBeenCalled();
    delete t.ctx.request.headers["stripe-signature"];
    await t.run();
    expect(t.ctx.status).toBe(400);
    t.ctx.request.headers["stripe-signature"] = "sig";
    t.ctx.request.rawBody = "";
    await t.run();
    expect(t.ctx.status).toBe(400);
  });
  it("lets Stripe retry transient provider failures without clearing caches", async () => {
    const t = setup(subscriptionEvent());
    t.stripe.listSubscriptions.mockRejectedValue(
      new Error("unavailable") as never,
    );
    await t.run();
    expect(t.ctx.status).toBe(400);
    expect(t.paidCustomer.updatePeriodIfUnchanged).not.toHaveBeenCalled();
  });
  it("passes verified checkout metadata to customer binding creation", async () => {
    const object = {
      customer: "cus_synthetic",
      metadata: { userId: "usr_synthetic", clientId: BILLING_CLIENT_ID },
    };
    const t = setup(
      subscriptionEvent({
        type: "checkout.session.completed",
        data: { object },
      }),
    );
    await t.run();
    expect(t.stripe.handleCheckoutSessionCompleted).toHaveBeenCalledWith(
      object,
      BILLING_CLIENT_ID,
      "usr_synthetic",
    );
  });
});

describe("a scheduled plan change taking effect", () => {
  it("refreshes the binding from the subscription's new price at the phase change", async () => {
    // Stripe moves the subscription to the scheduled price and sends
    // customer.subscription.updated; the schedule may still be attached.
    const PERIOD_END = 2_100_000_000;
    const t = setup(subscriptionEvent());
    const binding = {
      id: "binding_synthetic",
      userId: "usr_synthetic",
      clientId: BILLING_CLIENT_ID,
      stripeCustomerId: "cus_synthetic",
    };
    t.paidCustomer.findByUserId.mockResolvedValue([binding] as never);
    t.stripe.listSubscriptions.mockResolvedValue([
      {
        id: "sub_synthetic",
        customer: "cus_synthetic",
        clientId: BILLING_CLIENT_ID,
        livemode: true,
        status: "active",
        schedule: "sub_sched_synthetic",
        items: {
          data: [
            {
              price: { id: "price_1RrSOGEqsEqs2tLVFnyB34qG" },
              current_period_end: PERIOD_END,
            },
          ],
        },
      },
    ] as never);

    await t.run();

    expect(t.paidCustomer.updatePeriodIfUnchanged).toHaveBeenCalledWith(
      {},
      binding,
      new Date(PERIOD_END * 1000),
      SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
    );
  });
});

describe("paid invoices", () => {
  const paidInvoice = (
    metadata: Record<string, string> = {},
    invoice: Record<string, unknown> = {},
  ) => ({
    id: "evt_synthetic",
    livemode: true,
    type: "invoice.paid",
    data: {
      object: {
        id: "in_synthetic",
        billing_reason: "subscription_create",
        amount_paid: 1499,
        customer: "cus_synthetic",
        metadata: {},
        parent: { subscription_details: { metadata } },
        ...invoice,
      },
    },
  });

  beforeEach(() => mockReportPurchase.mockClear());

  it("reports the purchase for the bound user", async () => {
    const t = setup(paidInvoice({ userId: "usr_synthetic" }));
    await t.run();
    expect(mockReportPurchase).toHaveBeenCalledWith(
      expect.objectContaining({ db: {}, analytics: ANALYTICS }),
      expect.objectContaining({ id: "in_synthetic" }),
      "usr_synthetic",
    );
    expect(t.ctx.body.processed).toBe(true);
  });

  it("does no lookup for a renewal, which is not a purchase", async () => {
    const t = setup(
      paidInvoice(
        { userId: "usr_synthetic" },
        { billing_reason: "subscription_cycle" },
      ),
    );
    await t.run();
    expect(
      t.paidCustomer.findByStripeCustomerIdAndClientId,
    ).not.toHaveBeenCalled();
    expect(mockReportPurchase).not.toHaveBeenCalled();
    expect(t.ctx.status).toBe(200);
  });

  it("asks Stripe to redeliver when the report failed", async () => {
    mockReportPurchase.mockResolvedValueOnce("failed");
    const t = setup(paidInvoice({ userId: "usr_synthetic" }));
    await t.run();
    expect(t.ctx.status).toBe(400);
  });

  it("reports a first Checkout whose invoice arrives before the customer is bound", async () => {
    const t = setup(paidInvoice({ userId: "usr_new" }));
    t.paidCustomer.findByStripeCustomerIdAndClientId.mockResolvedValue(
      null as never,
    );
    await t.run();
    expect(mockReportPurchase).toHaveBeenCalledWith(
      expect.anything(),
      expect.anything(),
      "usr_new",
    );
  });

  it.each([
    ["names another user than the binding", { userId: "usr_other" }],
    [
      "belongs to another billing client",
      { userId: "usr_synthetic", clientId: "beancount-web-dev" },
    ],
  ])("reports nothing when the subscription %s", async (_label, metadata) => {
    const t = setup(paidInvoice(metadata));
    await t.run();
    expect(mockReportPurchase).not.toHaveBeenCalled();
    expect(t.ctx.status).toBe(200);
    expect(t.ctx.body.processed).toBe(false);
  });

  it("reports nothing when no user can be named", async () => {
    const t = setup(paidInvoice());
    t.paidCustomer.findByStripeCustomerIdAndClientId.mockResolvedValue(
      null as never,
    );
    await t.run();
    expect(mockReportPurchase).not.toHaveBeenCalled();
  });
});
