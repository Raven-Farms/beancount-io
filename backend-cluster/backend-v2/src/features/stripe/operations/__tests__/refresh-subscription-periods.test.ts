import { refreshSubscriptionPeriods } from "../refresh-subscription-periods";
import { SUBSCRIPTION_PERIOD_VERIFICATION_VERSION } from "../../service/subscription-plan";
const clientId = "beancount-web-prod";
const period = new Date(2000000000000);
function setup() {
  const retired = {
    id: "old",
    userId: "u",
    clientId: "beancount-web-dev",
    stripeCustomerId: "cus_old",
    currentPeriodEnd: new Date(2100000000000),
  };
  const live = {
    id: "live",
    userId: "u",
    clientId,
    stripeCustomerId: "cus_live",
    updatedAt: new Date(0),
  };
  const stripe = {
    listSubscriptions: jest.fn(async () => [
      {
        id: "sub_live",
        clientId,
        customer: "cus_live",
        livemode: true,
        status: "active",
        items: {
          data: [
            {
              price: { id: "price_1SyPdcEqsEqs2tLVCWEgU1PZ" },
              current_period_end: 2000000000,
            },
          ],
        },
      },
    ]),
  };
  const model = {
    findByUserId: jest.fn(async () => [retired, live]),
    updatePeriodIfUnchanged: jest.fn(async () => true),
  };
  return {
    stripe,
    model,
    live,
    retired,
    run: () =>
      refreshSubscriptionPeriods(
        stripe as any,
        { paidCustomer: model } as any,
        {} as any,
        "u",
      ),
  };
}
describe("owned renewal cache", () => {
  it("updates the live binding regardless of row order and leaves retired history unchanged", async () => {
    const t = setup();
    const old = JSON.stringify(t.retired);
    await t.run();
    expect(t.model.updatePeriodIfUnchanged).toHaveBeenCalledTimes(1);
    expect(t.model.updatePeriodIfUnchanged).toHaveBeenCalledWith(
      {},
      t.live,
      period,
      SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
    );
    expect(JSON.stringify(t.retired)).toBe(old);
  });
  it("does not write on repeated refresh or provider failure", async () => {
    const t = setup();
    Object.assign(t.live, {
      currentPeriodEnd: period,
      periodVerificationVersion: SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
    });
    await t.run();
    expect(t.model.updatePeriodIfUnchanged).not.toHaveBeenCalled();
    t.stripe.listSubscriptions.mockRejectedValue(
      new Error("provider unavailable"),
    );
    await expect(t.run()).rejects.toThrow("provider unavailable");
    expect(t.model.updatePeriodIfUnchanged).not.toHaveBeenCalled();
  });
  it("verifies a historical period even when Stripe returns the same date", async () => {
    const t = setup();
    Object.assign(t.live, { currentPeriodEnd: period });
    await t.run();
    expect(t.model.updatePeriodIfUnchanged).toHaveBeenCalledWith(
      {},
      t.live,
      period,
      SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
    );
  });
  it("leaves an unverified historical period untouched on provider failure", async () => {
    const t = setup();
    Object.assign(t.live, { currentPeriodEnd: period });
    t.stripe.listSubscriptions.mockRejectedValue(
      new Error("provider unavailable"),
    );
    await expect(t.run()).rejects.toThrow("provider unavailable");
    expect(t.model.updatePeriodIfUnchanged).not.toHaveBeenCalled();
    expect(t.live).not.toHaveProperty("periodVerificationVersion");
  });
  it("clears an expired live cache and never borrows a foreign customer's period", async () => {
    const t = setup();
    Object.assign(t.live, { currentPeriodEnd: period });
    t.stripe.listSubscriptions.mockResolvedValue([
      { ...(await t.stripe.listSubscriptions())[0], customer: "cus_foreign" },
    ]);
    await t.run();
    expect(t.model.updatePeriodIfUnchanged).toHaveBeenCalledWith(
      {},
      t.live,
      null,
      SUBSCRIPTION_PERIOD_VERIFICATION_VERSION,
    );
  });
});
