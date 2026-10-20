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
    [sub([org], { status: "past_due" })],
    [],
  ])(
    "does not invent a paid entitlement for unsupported subscriptions",
    async (...subscriptions) => {
      expect(
        await getUserTier(deps(subscriptions as ClientSubscription[])),
      ).toBe(SubscriptionTier.FREE);
    },
  );
  it("retains fail-closed error behavior", async () => {
    const params = deps([]);
    params.stripe.listSubscriptions.mockRejectedValue(
      new Error("provider unavailable"),
    );
    expect(await getUserTier(params)).toBe(SubscriptionTier.FREE);
  });
  it("uses Organization quotas for the same live subscription despite historical test cache", async () => {
    expect(await getUserTierLimits(deps([sub([org])]))).toMatchObject({
      maxLedgers: 100,
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

describe("SELF_HOSTED_TIER", () => {
  const originalEnv = process.env;
  afterEach(() => {
    process.env = originalEnv;
  });

  it("gives every user the configured tier without asking Stripe", async () => {
    process.env = { ...originalEnv, SELF_HOSTED_TIER: "ENTERPRISE" };
    let fresh!: typeof import("../get-user-tier");
    jest.isolateModules(() => {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      fresh = require("../get-user-tier");
    });
    const params = deps([]);
    expect(await fresh.getUserTier(params)).toBe(SubscriptionTier.ENTERPRISE);
    expect((await fresh.getUserTierLimits(params)).maxLedgers).toBe(-1);
    expect(params.stripe.listSubscriptions).not.toHaveBeenCalled();
  });

  it("leaves Stripe in charge when unset", async () => {
    const params = deps([]);
    expect(await getUserTier(params)).toBe(SubscriptionTier.FREE);
    expect(params.stripe.listSubscriptions).toHaveBeenCalledTimes(1);
  });
});
