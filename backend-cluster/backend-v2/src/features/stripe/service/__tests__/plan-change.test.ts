import {
  classifyPlanChange,
  PLAN_CHANGE_EFFECT,
  type PlanChangeClassification,
} from "../plan-change";
import { BILLING_CLIENT_ID, SUBSCRIPTION_CONFIG } from "../stripe";
import { tierRank } from "../subscription-plan";

const plans = SUBSCRIPTION_CONFIG[BILLING_CLIENT_ID].plans;
const plan = (priceId: string) => {
  const found = plans.find((candidate) => candidate.priceId === priceId);
  if (!found) throw new Error(`unconfigured price ${priceId}`);
  return found;
};

const LEGACY_PREMIUM_MONTHLY = "price_1L9ccEEqsEqs2tLVKPRV17wb";
const PREMIUM_MONTHLY = "price_1RrSOGEqsEqs2tLVFnyB34qG";
const PREMIUM_YEARLY = "price_1L9ccEEqsEqs2tLVbeBgHm9p";
const GROWTH_MONTHLY = "price_1SyPdaEqsEqs2tLViLPUDoVi";
const GROWTH_YEARLY = "price_1SyPdbEqsEqs2tLV7PJyWZed";
const ORGANIZATION_YEARLY = "price_1SyPdfEqsEqs2tLVmK6zCrP6";

describe("classifyPlanChange (PRFAQ005 question 14)", () => {
  it.each<[string, string | null, string, PlanChangeClassification]>([
    ["no subscription yet", null, PREMIUM_YEARLY, { kind: "NEW" }],
    [
      "the price already held",
      PREMIUM_MONTHLY,
      PREMIUM_MONTHLY,
      { refusal: "CURRENT_PLAN" },
    ],
    [
      "a legacy price to today's on the same tier and cycle",
      LEGACY_PREMIUM_MONTHLY,
      PREMIUM_MONTHLY,
      { refusal: "SAME_TIER_AND_CYCLE" },
    ],
    [
      "monthly to yearly on one tier",
      PREMIUM_MONTHLY,
      PREMIUM_YEARLY,
      { kind: "TO_YEARLY" },
    ],
    [
      "a higher tier on the same cycle",
      PREMIUM_MONTHLY,
      GROWTH_MONTHLY,
      { kind: "UPGRADE" },
    ],
    [
      "a higher tier while moving to yearly",
      PREMIUM_MONTHLY,
      GROWTH_YEARLY,
      { kind: "TO_YEARLY" },
    ],
    [
      "a higher tier while leaving yearly",
      PREMIUM_YEARLY,
      GROWTH_MONTHLY,
      { kind: "SPLIT" },
    ],
    [
      "yearly to monthly on one tier",
      GROWTH_YEARLY,
      GROWTH_MONTHLY,
      { kind: "TO_MONTHLY" },
    ],
    [
      "a lower tier on the same cycle",
      ORGANIZATION_YEARLY,
      GROWTH_YEARLY,
      { kind: "DOWNGRADE" },
    ],
    [
      "a lower tier while moving to yearly",
      GROWTH_MONTHLY,
      PREMIUM_YEARLY,
      { kind: "DOWNGRADE" },
    ],
  ])("classifies %s", (_name, current, target, expected) => {
    expect(
      classifyPlanChange(current ? plan(current) : null, plan(target)),
    ).toEqual(expected);
  });

  describe("over every configured price pair", () => {
    const pairs = plans.flatMap((current) =>
      plans.map((target) => [current, target] as const),
    );

    it("covers the whole catalog", () => {
      expect(pairs.length).toBe(plans.length ** 2);
      expect(plans.length).toBeGreaterThanOrEqual(7);
    });

    it.each(pairs)(
      "%# refuses exactly the no-gain choices and otherwise names one kind",
      (current, target) => {
        const result = classifyPlanChange(current, target);
        const noGain =
          current.priceId === target.priceId ||
          (current.tier === target.tier &&
            current.interval === target.interval);
        expect("refusal" in result).toBe(noGain);
        if ("refusal" in result) return;

        const effect = PLAN_CHANGE_EFFECT[result.kind];
        const lowerTier = tierRank(target.tier) < tierRank(current.tier);
        const leavesYearly =
          current.interval === "year" && target.interval === "month";
        // Gains apply now; any loss waits for the end of the paid period.
        expect(effect).toBe(
          lowerTier || leavesYearly ? "SCHEDULED" : "IMMEDIATE",
        );
        expect(result.kind === "DOWNGRADE").toBe(lowerTier);
      },
    );
  });
});
