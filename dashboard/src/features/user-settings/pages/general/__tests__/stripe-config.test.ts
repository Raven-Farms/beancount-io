import { readFileSync } from "fs";
import { join } from "path";
import { describe, it, expect } from "vitest";
import { tierInfoByKey } from "@/common/lib/subscription/tier-config";
import {
  BILLING_CYCLES,
  LEGACY_PRICE_IDS,
  SUBSCRIPTION_TIERS,
  cyclePrice,
  monthlyEquivalent,
  planForPrice,
  stripePlanConfig,
  yearlySaving,
} from "../stripe-config";

describe("live billing catalog", () => {
  it("keeps all purchasable tiers on the live client even with a retired URL switch", () => {
    window.history.replaceState({}, "", "/settings/general?env=dev");
    expect(stripePlanConfig.clientId).toBe("beancount-web-prod");
    expect(stripePlanConfig.organization.monthly).toBe(
      "price_1SyPdcEqsEqs2tLVCWEgU1PZ",
    );
    expect(stripePlanConfig.premium.yearly).toBe(
      "price_1US5htEqsEqs2tLVENCzLaZB",
    );
    expect(JSON.stringify(stripePlanConfig)).not.toContain("beancount-web-dev");
    window.history.replaceState({}, "", "/");
  });

  it("still names the plan a legacy price bills, so a change scheduled onto it keeps its label", () => {
    expect(planForPrice("price_1L9ccEEqsEqs2tLVbeBgHm9p")).toEqual({
      tier: "premium",
      cycle: "yearly",
    });
    expect(planForPrice("price_1L9ccEEqsEqs2tLVKPRV17wb")).toEqual({
      tier: "premium",
      cycle: "monthly",
    });
    expect(planForPrice("price_unknown")).toBeNull();
  });

  it.each(SUBSCRIPTION_TIERS)(
    "quotes %s yearly as the yearly amount over twelve, a 20% saving",
    (tier) => {
      const { monthlyAmount, yearlyAmount } = stripePlanConfig[tier];
      expect(monthlyEquivalent(yearlyAmount, "yearly")).toBe(
        Math.round(yearlyAmount / 12),
      );
      expect(yearlySaving(tier)).toEqual({
        saving: monthlyAmount * 12 - yearlyAmount,
        percent: 20,
      });
    },
  );
});

/** The backend's plans, read from its source in this monorepo. */
function backendPlans() {
  const source = readFileSync(
    join(
      __dirname,
      "../../../../../../../backend-cluster/backend-v2/src/features/stripe/service/stripe.ts",
    ),
    "utf-8",
  );
  const start = source.indexOf("plans: [");
  if (start === -1 || source.indexOf("plans: [", start + 1) !== -1) {
    throw new Error("expected exactly one plans array in the backend config");
  }
  const plans = source
    .slice(start, source.indexOf("\n    ],", start))
    .replace(/\/\/.*$/gm, "");
  return plans
    .split(/priceId: /)
    .slice(1)
    .map((block) => ({
      priceId: /^"(price_\w+)"/.exec(block)?.[1],
      interval: /interval: "(month|year)"/.exec(block)?.[1],
      tier: /tier: SubscriptionTier\.(\w+)/.exec(block)?.[1],
      retired: /retired: true/.test(block.split("}")[0]),
    }));
}

describe("dashboard prices agree with the backend's SUBSCRIPTION_CONFIG", () => {
  const plans = backendPlans();
  const offered = SUBSCRIPTION_TIERS.flatMap((tier) =>
    BILLING_CYCLES.map((cycle) => ({
      tier,
      cycle,
      ...cyclePrice(tier, cycle),
    })),
  );

  it("reads every backend plan", () => {
    expect(plans.length).toBeGreaterThanOrEqual(offered.length);
    for (const plan of plans) {
      expect(plan.priceId && plan.interval && plan.tier).toBeTruthy();
    }
  });

  it.each(offered)(
    "offers $tier $cycle at a current backend price for that tier and cycle",
    ({ tier, cycle, priceId }) => {
      expect(plans.find((plan) => plan.priceId === priceId)).toEqual({
        priceId,
        interval: cycle === "yearly" ? "year" : "month",
        tier: tierInfoByKey(tier).userTier,
        retired: false,
      });
    },
  );

  it("offers every price the backend still sells, and labels every other one legacy", () => {
    const offeredIds = new Set(offered.map((each) => each.priceId));
    for (const plan of plans) {
      if (plan.retired) {
        expect(LEGACY_PRICE_IDS.has(plan.priceId!)).toBe(true);
      } else {
        expect(offeredIds.has(plan.priceId!)).toBe(true);
      }
    }
    expect(LEGACY_PRICE_IDS.size).toBe(
      plans.filter((plan) => plan.retired).length,
    );
  });
});
