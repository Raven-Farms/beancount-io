import { describe, expect, it } from "vitest";
import { featuresGained } from "../plan-features";

describe("featuresGained", () => {
  it("lists only what the higher plan adds", () => {
    expect(featuresGained("FREE", "PREMIUM")).toEqual([
      "userSettings.featureAutomaticBackups",
    ]);
    expect(featuresGained("PREMIUM", "ORGANIZATION")).toEqual([
      "userSettings.featureAutomationIntegrations",
      "userSettings.featureOidcSso",
      "userSettings.featureMultiEntity",
    ]);
  });

  it("adds nothing on the same tier or a lower one", () => {
    expect(featuresGained("GROWTH", "GROWTH")).toEqual([]);
    expect(featuresGained("ORGANIZATION", "PREMIUM")).toEqual([]);
  });
});
