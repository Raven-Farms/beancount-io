import "reflect-metadata";
import Router from "@koa/router";
import { setStripeWebhookHandler } from "../stripe-webhook-handler";
import { BILLING_CLIENT_ID } from "../../service/stripe";
import type { AppLayers } from "@/foundation/composition";

jest.mock("@/features/stripe/service/stripe", () => ({
  ...jest.requireActual("@/features/stripe/service/stripe"),
  SUBSCRIPTION_CONFIG: {
    "beancount-web-prod": { webhookSecret: "whsec_synthetic" },
  },
}));
jest.mock("@/server/rest/openapi-registry", () => ({
  registerRoute: jest.fn(),
}));

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
  setStripeWebhookHandler(router, {
    services: { stripe },
    database: { db: {}, models: { paidCustomer } },
  } as unknown as AppLayers);
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
    expect(t.stripe.listSubscriptions).toHaveBeenCalledWith("usr_synthetic", {
      bindings: [],
      status: "active",
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
