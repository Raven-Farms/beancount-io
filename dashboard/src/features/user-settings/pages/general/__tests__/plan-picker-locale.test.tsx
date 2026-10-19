import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PlanPicker } from "../subscription-plan-picker";
import { MOCK_TIER_QUOTAS } from "./subscription-test-utils";

vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ i18n: { language: "fa" } }),
}));
vi.mock("@/common/analytics", () => ({ track: vi.fn() }));

const t = (key: string, params?: Record<string, string | number>) =>
  params ? `${key}(${Object.values(params).join(",")})` : key;

function renderPicker() {
  render(
    <PlanPicker
      tier="FREE"
      currentInterval={null}
      quotaByUserTier={Object.fromEntries(
        MOCK_TIER_QUOTAS.map((quota) => [quota.tier, quota]),
      )}
      t={t}
      busy={false}
      onChoose={vi.fn()}
    />,
  );
}

const card = (tier: string) => within(screen.getByTestId(`plan-card-${tier}`));

describe("PlanPicker in a language with its own digits", () => {
  it("writes the yearly saving in the app language's digits", () => {
    renderPicker();

    expect(
      card("PREMIUM").getByText("userSettings.saveYearlyPercent(۲۰)"),
    ).toBeInTheDocument();
  });

  it("names Enterprise's AI allowance rather than a bare Unlimited", () => {
    renderPicker();

    expect(
      card("ENTERPRISE").getByText("userSettings.unlimitedAiTokens"),
    ).toBeInTheDocument();
    expect(
      card("ENTERPRISE").queryByText("userSettings.unlimited"),
    ).not.toBeInTheDocument();
  });
});
