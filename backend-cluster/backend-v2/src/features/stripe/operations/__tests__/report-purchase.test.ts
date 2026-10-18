import type Stripe from "stripe";
import {
  isPurchase,
  purchasePayload,
  reportPurchase,
} from "../report-purchase";
import { SUBSCRIPTION_CONFIG, BILLING_CLIENT_ID } from "../../service/stripe";

const PLANS = SUBSCRIPTION_CONFIG[BILLING_CLIENT_ID].plans;
const GROWTH_YEARLY = PLANS.find(
  (plan) => plan.tier === "GROWTH" && plan.interval === "year",
)!;
const GROWTH_MONTHLY = PLANS.find(
  (plan) => plan.tier === "GROWTH" && plan.interval === "month",
)!;

function line(priceId: string, amount: number) {
  return { amount, pricing: { price_details: { price: priceId } } };
}

function invoice(
  overrides: Record<string, unknown> = {},
): Stripe.Invoice & { id: string } {
  return {
    id: "in_synthetic",
    billing_reason: "subscription_create",
    amount_paid: 95988,
    currency: "usd",
    customer: "cus_synthetic",
    customer_email: "reader@example.com",
    lines: { data: [line(GROWTH_YEARLY.priceId, 95988)] },
    ...overrides,
  } as unknown as Stripe.Invoice & { id: string };
}

const CONFIGURED = {
  gaMeasurementId: "G-SYNTHETIC",
  measurementProtocolSecret: "mp_secret_synthetic",
};

function deps(overrides: Partial<Parameters<typeof reportPurchase>[0]> = {}) {
  const claim = jest.fn(async () => true);
  const release = jest.fn(async () => undefined);
  const fetch = jest.fn(async () => new Response(null, { status: 204 }));
  return {
    claim,
    release,
    fetch,
    deps: {
      models: { reportedPurchase: { claim, release } },
      db: {} as never,
      analytics: CONFIGURED,
      plans: PLANS,
      fetch: fetch as unknown as typeof globalThis.fetch,
      ...overrides,
    },
  };
}

describe("purchasePayload", () => {
  it("reports a Checkout's first invoice with its value, cycle and plan", () => {
    const payload = purchasePayload(invoice(), "usr_synthetic", PLANS);
    expect(payload).toEqual({
      client_id: expect.stringMatching(/^server\.[0-9a-f]{20}$/),
      user_id: "usr_synthetic",
      events: [
        {
          name: "purchase",
          params: {
            transaction_id: "in_synthetic",
            value: 959.88,
            currency: "USD",
            billing_reason: "subscription_create",
            items: [
              {
                item_id: GROWTH_YEARLY.priceId,
                item_name: "GROWTH",
                item_variant: "year",
                price: 959.88,
                quantity: 1,
              },
            ],
          },
        },
      ],
    });
  });

  it("carries no personal or customer data", () => {
    const body = JSON.stringify(
      purchasePayload(invoice(), "usr_synthetic", PLANS),
    );
    expect(body).not.toContain("reader@example.com");
    expect(body).not.toContain("cus_synthetic");
  });

  it("keeps the new plan of an immediate change, not the old plan's credit", () => {
    const payload = purchasePayload(
      invoice({
        billing_reason: "subscription_update",
        amount_paid: 4250,
        lines: {
          data: [
            line(GROWTH_MONTHLY.priceId, -750),
            line(GROWTH_YEARLY.priceId, 5000),
          ],
        },
      }),
      "usr_synthetic",
      PLANS,
    );
    expect(payload.events[0].params).toMatchObject({
      value: 42.5,
      billing_reason: "subscription_update",
      items: [{ item_id: GROWTH_YEARLY.priceId, price: 50 }],
    });
  });

  it("reads amounts in the currency's own minor unit", () => {
    const payload = purchasePayload(
      invoice({
        currency: "jpy",
        amount_paid: 1500,
        lines: { data: [line(GROWTH_YEARLY.priceId, 1500)] },
      }),
      "usr_synthetic",
      PLANS,
    );
    expect(payload.events[0].params).toMatchObject({
      value: 1500,
      currency: "JPY",
      items: [{ price: 1500 }],
    });
  });

  it("derives the same client id for the same user", () => {
    const first = purchasePayload(invoice(), "usr_synthetic", PLANS);
    const second = purchasePayload(
      invoice({ id: "in_other" }),
      "usr_synthetic",
      PLANS,
    );
    expect(first.client_id).toBe(second.client_id);
  });
});

describe("isPurchase", () => {
  it.each([
    ["a Checkout's first invoice", {}, true],
    ["an immediate change", { billing_reason: "subscription_update" }, true],
    ["a renewal", { billing_reason: "subscription_cycle" }, false],
    ["a fully discounted invoice", { amount_paid: 0 }, false],
    ["a manual invoice", { billing_reason: "manual" }, false],
  ])("%s", (_label, overrides, expected) => {
    expect(isPurchase(invoice(overrides))).toBe(expected);
  });
});

describe("reportPurchase", () => {
  it("claims the invoice, then sends it to the configured stream", async () => {
    const t = deps();
    await expect(
      reportPurchase(t.deps, invoice(), "usr_synthetic"),
    ).resolves.toBe("reported");
    expect(t.claim).toHaveBeenCalledWith({}, "in_synthetic");
    const [url, init] = t.fetch.mock.calls[0] as unknown as [URL, RequestInit];
    expect(url.origin + url.pathname).toBe(
      "https://www.google-analytics.com/mp/collect",
    );
    expect(url.searchParams.get("measurement_id")).toBe("G-SYNTHETIC");
    expect(url.searchParams.get("api_secret")).toBe("mp_secret_synthetic");
    expect(JSON.parse(init.body as string).events[0].name).toBe("purchase");
  });

  it("sends nothing for a retried delivery of an invoice already reported", async () => {
    const t = deps();
    t.claim.mockResolvedValue(false);
    await expect(
      reportPurchase(t.deps, invoice(), "usr_synthetic"),
    ).resolves.toBe("already_reported");
    expect(t.fetch).not.toHaveBeenCalled();
  });

  it.each([
    ["measurement id", { gaMeasurementId: "", measurementProtocolSecret: "x" }],
    ["API secret", { gaMeasurementId: "G-X", measurementProtocolSecret: "" }],
  ])("does nothing without a %s", async (_label, analytics) => {
    const t = deps({ analytics });
    await expect(
      reportPurchase(t.deps, invoice(), "usr_synthetic"),
    ).resolves.toBe("unconfigured");
    expect(t.claim).not.toHaveBeenCalled();
    expect(t.fetch).not.toHaveBeenCalled();
  });

  it.each([
    ["the network fails", () => Promise.reject(new TypeError("fetch failed"))],
    ["GA4 refuses", async () => new Response(null, { status: 500 })],
  ])(
    "gives the claim back for Stripe's retry when %s",
    async (_label, send) => {
      const t = deps();
      t.fetch.mockImplementation(send as never);
      await expect(
        reportPurchase(t.deps, invoice(), "usr_synthetic"),
      ).resolves.toBe("failed");
      expect(t.release).toHaveBeenCalledWith({}, "in_synthetic");
    },
  );

  it("keeps the claim once GA4 accepted the purchase", async () => {
    const t = deps();
    await reportPurchase(t.deps, invoice(), "usr_synthetic");
    expect(t.release).not.toHaveBeenCalled();
  });

  it("throws when the claim cannot be recorded, so Stripe retries", async () => {
    const t = deps();
    t.claim.mockRejectedValue(new Error("database unavailable"));
    await expect(
      reportPurchase(t.deps, invoice(), "usr_synthetic"),
    ).rejects.toThrow("database unavailable");
    expect(t.fetch).not.toHaveBeenCalled();
  });
});
