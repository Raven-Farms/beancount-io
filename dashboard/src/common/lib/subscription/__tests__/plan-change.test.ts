import { describe, expect, it } from "vitest";
import {
  IMMEDIATE_CHOICES,
  planChoice,
  planValue,
  type PlanChoice,
  type PlanInterval,
} from "../plan-change";
import type { UserTier } from "@/common/hooks/use-user-limits";

type Plan = { tier: UserTier; interval: PlanInterval | null };

describe("planChoice (mirrors the server's PRFAQ005 question 14 rule)", () => {
  it.each<[string, Plan, Plan, PlanChoice]>([
    [
      "a free user choosing a paid plan",
      { tier: "FREE", interval: null },
      { tier: "PREMIUM", interval: "year" },
      "NEW",
    ],
    [
      "a free user's own plan",
      { tier: "FREE", interval: null },
      { tier: "FREE", interval: null },
      "CURRENT",
    ],
    [
      "the plan already held",
      { tier: "PREMIUM", interval: "month" },
      { tier: "PREMIUM", interval: "month" },
      "CURRENT",
    ],
    [
      "monthly to yearly on one tier",
      { tier: "PREMIUM", interval: "month" },
      { tier: "PREMIUM", interval: "year" },
      "TO_YEARLY",
    ],
    [
      "a higher tier on the same cycle",
      { tier: "PREMIUM", interval: "month" },
      { tier: "GROWTH", interval: "month" },
      "UPGRADE",
    ],
    [
      "a higher tier while moving to yearly",
      { tier: "PREMIUM", interval: "month" },
      { tier: "GROWTH", interval: "year" },
      "TO_YEARLY",
    ],
    [
      "a higher tier while leaving yearly",
      { tier: "PREMIUM", interval: "year" },
      { tier: "GROWTH", interval: "month" },
      "SPLIT",
    ],
    [
      "yearly to monthly on one tier",
      { tier: "GROWTH", interval: "year" },
      { tier: "GROWTH", interval: "month" },
      "TO_MONTHLY",
    ],
    [
      "a lower tier",
      { tier: "ORGANIZATION", interval: "year" },
      { tier: "GROWTH", interval: "year" },
      "DOWNGRADE",
    ],
    [
      "Free from a paid plan",
      { tier: "PREMIUM", interval: "month" },
      { tier: "FREE", interval: null },
      "DOWNGRADE",
    ],
    [
      "a paid tier held without a subscription",
      { tier: "PREMIUM", interval: null },
      { tier: "GROWTH", interval: "month" },
      "NEW",
    ],
  ])("classifies %s", (_name, current, target, expected) => {
    expect(planChoice(current, target)).toBe(expected);
  });

  it("applies only gains immediately", () => {
    expect([...IMMEDIATE_CHOICES].sort()).toEqual([
      "NEW",
      "TO_YEARLY",
      "UPGRADE",
    ]);
  });
});

describe("planValue", () => {
  it.each([
    ["PREMIUM", "monthly", "premium_monthly"],
    ["GROWTH", "yearly", "growth_yearly"],
    // No subscription, or a tier without a billing cycle, is the tier alone.
    ["PREMIUM", null, "premium"],
    ["FREE", null, "free"],
    ["FREE", "yearly", "free"],
    ["ENTERPRISE", "yearly", "enterprise"],
  ] as const)("%s on %s is %s", (tier, cycle, expected) => {
    expect(planValue(tier, cycle)).toBe(expected);
  });
});
