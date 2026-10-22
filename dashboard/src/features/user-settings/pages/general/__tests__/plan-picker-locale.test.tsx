import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

/**
 * The selected cycle's primary fill disappears in forced colors, so Yearly
 * and Monthly painted alike (w4/m43). Each cycle carries `forced-selected`
 * behind its own pressed state; the paint was measured in a real browser.
 */
describe("PlanPicker billing cycle under forced colors", () => {
  const pressed = () =>
    within(screen.getByRole("group", { name: "userSettings.billingCycle" }))
      .getAllByRole("button")
      .filter((cycle) => {
        expect(cycle).toHaveClass("aria-pressed:forced-selected");
        return cycle.getAttribute("aria-pressed") === "true";
      })
      .map((cycle) => cycle.textContent);

  it("gates the highlight on the chosen cycle, which follows a new choice", async () => {
    const user = userEvent.setup();
    renderPicker();
    expect(pressed()).toEqual(["userSettings.yearly"]);

    await user.click(
      screen.getByRole("button", { name: "userSettings.monthly" }),
    );
    expect(pressed()).toEqual(["userSettings.monthly"]);
  });
});
