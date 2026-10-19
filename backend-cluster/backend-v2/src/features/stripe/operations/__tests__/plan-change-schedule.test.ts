import type Stripe from "stripe";
import { BILLING_CLIENT_ID, SUBSCRIPTION_CONFIG } from "../../service/stripe";
import { pendingChange } from "../plan-change-schedule";

const PLANS = SUBSCRIPTION_CONFIG[BILLING_CLIENT_ID].plans;
const PREMIUM_MONTHLY = "price_1RrSOGEqsEqs2tLVFnyB34qG";
const GROWTH_MONTHLY = "price_1SyPdaEqsEqs2tLViLPUDoVi";
const START = 1_790_000_000;
const END = 1_792_000_000;

function subscription(
  schedule: unknown,
  priceId = GROWTH_MONTHLY,
): Stripe.Subscription {
  return {
    schedule,
    items: { data: [{ price: { id: priceId } }] },
  } as unknown as Stripe.Subscription;
}

function schedule(overrides: Record<string, unknown> = {}) {
  return {
    status: "active",
    current_phase: { start_date: START, end_date: END },
    phases: [
      { start_date: START, items: [{ price: GROWTH_MONTHLY }] },
      { start_date: END, items: [{ price: { id: PREMIUM_MONTHLY } }] },
    ],
    ...overrides,
  };
}

describe("pendingChange", () => {
  it("reads the next phase's plan and when it starts", () => {
    expect(pendingChange(subscription(schedule()), PLANS)).toEqual({
      priceId: PREMIUM_MONTHLY,
      effectiveAt: new Date(END * 1000),
    });
  });

  it.each([
    ["no schedule", null],
    ["a released schedule", schedule({ status: "released" })],
    // The change already took effect: the schedule is in its last phase.
    [
      "a schedule in its last phase",
      schedule({ current_phase: { start_date: END, end_date: END + 1 } }),
    ],
  ])("reports nothing pending for %s", (_label, value) => {
    expect(pendingChange(subscription(value), PLANS)).toBeNull();
  });

  it("reports nothing when the next phase keeps the current price", () => {
    expect(
      pendingChange(subscription(schedule(), PREMIUM_MONTHLY), PLANS),
    ).toBeNull();
  });

  it("refuses a schedule that was not expanded rather than report nothing", () => {
    expect(() => pendingChange(subscription("sub_sched_1"), PLANS)).toThrow(
      "expanded",
    );
  });

  it("finds a change in a later phase when the next one keeps the price", () => {
    const later = END + 1_000_000;
    expect(
      pendingChange(
        subscription(
          schedule({
            phases: [
              { start_date: START, items: [{ price: GROWTH_MONTHLY }] },
              { start_date: END, items: [{ price: GROWTH_MONTHLY }] },
              { start_date: later, items: [{ price: PREMIUM_MONTHLY }] },
            ],
          }),
        ),
        PLANS,
      ),
    ).toEqual({
      priceId: PREMIUM_MONTHLY,
      effectiveAt: new Date(later * 1000),
    });
  });

  it("names a price outside the plans when that is what a phase adds", () => {
    expect(
      pendingChange(
        subscription(
          schedule({
            phases: [
              { start_date: START, items: [{ price: GROWTH_MONTHLY }] },
              { start_date: END, items: [{ price: "price_custom" }] },
            ],
          }),
        ),
        PLANS,
      )?.priceId,
    ).toBe("price_custom");
  });
});
