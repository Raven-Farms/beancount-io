import Stripe from "stripe";
import { getUserTier, getUserTierLimits } from "../get-user-tier";
import { BILLING_CLIENT_ID, SubscriptionTier } from "../../service/stripe";
import { subscriptionPeriodEnd } from "../../service/subscription-plan";
import type { ClientSubscription } from "../../service/subscription-plan";

const premium = "price_1RrSOGEqsEqs2tLVFnyB34qG";
const org = "price_1SyPdcEqsEqs2tLVCWEgU1PZ";
function sub(prices: string[], overrides = {}): ClientSubscription {
  return {
    id: "sub_synthetic",
    customer: "cus_synthetic",
    clientId: BILLING_CLIENT_ID,
    livemode: true,
    status: "active",
    items: {
      data: prices.map((id) => ({
        price: { id },
        current_period_end: 2000000000,
      })),
    },
    ...overrides,
  } as ClientSubscription;
}
function deps(subscriptions: ClientSubscription[]) {
  return {
    stripe: { listSubscriptions: jest.fn(async () => subscriptions) },
    userId: "usr_synthetic",
    models: {
      paidCustomer: {
        findByUserIdWithActivePeriod: jest.fn(async () => ({
          clientId: "beancount-web-dev",
        })),
      },
    },
    postgresDb: {},
  } as any;
}

describe("subscription-bound tier", () => {
  it.each([
    [premium, SubscriptionTier.PREMIUM],
    [org, SubscriptionTier.ORGANIZATION],
    ["price_1L9ccEEqsEqs2tLVbeBgHm9p", SubscriptionTier.PREMIUM],
    ["price_1L9ccEEqsEqs2tLVKPRV17wb", SubscriptionTier.PREMIUM],
    ["price_1US5htEqsEqs2tLVENCzLaZB", SubscriptionTier.PREMIUM],
  ])("maps recognized price %s", async (price, tier) => {
    const params = deps([sub([price])]);
    expect(await getUserTier(params)).toBe(tier);
    expect(params.stripe.listSubscriptions).toHaveBeenCalledTimes(1);
    expect(
      params.models.paidCustomer.findByUserIdWithActivePeriod,
    ).not.toHaveBeenCalled();
  });
  it("examines every item and chooses the highest tier regardless of ordering", async () => {
    for (const subscriptions of [
      [sub([premium]), sub(["unknown", org])],
      [sub([org]), sub([premium])],
    ]) {
      expect(await getUserTier(deps(subscriptions))).toBe(
        SubscriptionTier.ORGANIZATION,
      );
    }
  });
  it.each([
    [sub([org], { clientId: "beancount-web-dev" })],
    [sub([org], { livemode: false })],
    [sub(["unknown"])],
    [sub([])],
    [sub([org], { status: "canceled" })],
    [sub([org], { status: "unpaid" })],
    [],
  ])(
    "does not invent a paid entitlement for unsupported subscriptions",
    async (...subscriptions) => {
      expect(
        await getUserTier(deps(subscriptions as ClientSubscription[])),
      ).toBe(SubscriptionTier.FREE);
    },
  );
  it("keeps the paid tier while a renewal is past due and Stripe retries", async () => {
    const retrying = {
      status: "past_due",
      latest_invoice: { status: "open", next_payment_attempt: 2000000000 },
    };
    const params = deps([sub([org], retrying)]);
    expect(await getUserTier(params)).toBe(SubscriptionTier.ORGANIZATION);
    expect(params.stripe.listSubscriptions).toHaveBeenCalledWith(
      "usr_synthetic",
      { status: "current" },
    );
  });
  it("drops the paid tier once Stripe stops retrying a past-due renewal", async () => {
    const exhausted = {
      status: "past_due",
      latest_invoice: { status: "open", next_payment_attempt: null },
    };
    expect(await getUserTier(deps([sub([org], exhausted)]))).toBe(
      SubscriptionTier.FREE,
    );
  });
  const outage = () =>
    new Stripe.errors.StripeConnectionError({
      type: "api_error",
      message: "Stripe down",
    });
  it("falls back to the last verified tier while Stripe is unavailable", async () => {
    const params = deps([]);
    params.stripe.listSubscriptions.mockRejectedValue(outage());
    params.stripe.lastVerifiedTier = jest.fn(
      async () => SubscriptionTier.GROWTH,
    );
    expect(await getUserTier(params)).toBe(SubscriptionTier.GROWTH);
  });
  it("stays Free while Stripe is unavailable when no verified tier is cached", async () => {
    const params = deps([]);
    params.stripe.listSubscriptions.mockRejectedValue(outage());
    params.stripe.lastVerifiedTier = jest.fn(async () => null);
    expect(await getUserTier(params)).toBe(SubscriptionTier.FREE);
    expect(params.stripe.lastVerifiedTier).toHaveBeenCalledWith(
      "usr_synthetic",
    );
  });
  it("never falls back for a failure that is not an outage, such as a binding mismatch", async () => {
    const params = deps([]);
    params.stripe.listSubscriptions.mockRejectedValue(
      new Error("Stripe subscription does not match its live customer binding"),
    );
    params.stripe.lastVerifiedTier = jest.fn(
      async () => SubscriptionTier.GROWTH,
    );
    expect(await getUserTier(params)).toBe(SubscriptionTier.FREE);
    expect(params.stripe.lastVerifiedTier).not.toHaveBeenCalled();
  });
  it("stays fail-closed when the cached tier cannot be read either", async () => {
    const params = deps([]);
    params.stripe.listSubscriptions.mockRejectedValue(outage());
    params.stripe.lastVerifiedTier = jest.fn(async () => {
      throw new Error("database down");
    });
    expect(await getUserTier(params)).toBe(SubscriptionTier.FREE);
  });
  it("retains fail-closed error behavior", async () => {
    const params = deps([]);
    params.stripe.listSubscriptions.mockRejectedValue(
      new Error("provider unavailable"),
    );
    expect(await getUserTier(params)).toBe(SubscriptionTier.FREE);
  });
  it("uses Organization quotas for the same live subscription despite historical test cache", async () => {
    expect(await getUserTierLimits(deps([sub([org])]))).toMatchObject({
      maxLedgers: 500,
      maxCollaboratorsPerLedger: 50,
    });
  });
  it("uses only recognized active item periods", () => {
    const subscription = sub([org]);
    subscription.items.data.push({
      price: { id: "unknown" },
      current_period_end: 2100000000,
    } as any);
    expect(subscriptionPeriodEnd([subscription])?.getTime()).toBe(
      2000000000000,
    );
    expect(
      subscriptionPeriodEnd([sub([org], { status: "canceled" })]),
    ).toBeNull();
  });
});
