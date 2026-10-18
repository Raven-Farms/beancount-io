import { describe, it, expect } from "vitest";
import { stripePlanConfig } from "../stripe-config";

describe("live billing catalog", () => {
  it("keeps all purchasable tiers on the live client even with a retired URL switch", () => {
    window.history.replaceState({}, "", "/settings/general?env=dev");
    expect(stripePlanConfig.clientId).toBe("beancount-web-prod");
    expect(stripePlanConfig.organization.monthly).toBe(
      "price_1SyPdcEqsEqs2tLVCWEgU1PZ",
    );
    expect(stripePlanConfig.premium.yearly).toBe(
      "price_1L9ccEEqsEqs2tLVbeBgHm9p",
    );
    expect(JSON.stringify(stripePlanConfig)).not.toContain("beancount-web-dev");
    window.history.replaceState({}, "", "/");
  });
});
