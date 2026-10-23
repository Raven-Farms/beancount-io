import { describe, expect, it } from "vitest";
import { describeTierQuota } from "../tier-quota-summary";
import { MOCK_TIER_QUOTAS } from "./subscription-test-utils";

const t = (key: string, params?: Record<string, string | number>) =>
  params ? `${key}(${JSON.stringify(params)})` : key;
const formatCount = (value: number) => value.toLocaleString("en-US");

describe("describeTierQuota", () => {
  it("names every unlimited allowance instead of printing -1", () => {
    const enterprise = MOCK_TIER_QUOTAS.find((q) => q.tier === "ENTERPRISE")!;

    expect(describeTierQuota(enterprise, t, formatCount)).toBe(
      [
        "userSettings.unlimitedAiTokens",
        "userSettings.unlimitedLedgers",
        "userSettings.unlimitedDirectives",
        "userSettings.unlimitedCollaborators",
      ].join(" · "),
    );
  });

  it("counts a limited plan's allowances", () => {
    const premium = MOCK_TIER_QUOTAS.find((q) => q.tier === "PREMIUM")!;

    expect(describeTierQuota(premium, t, formatCount)).toContain(
      'userSettings.aiTokensPerMonth({"count":"500,000"})',
    );
  });
});
