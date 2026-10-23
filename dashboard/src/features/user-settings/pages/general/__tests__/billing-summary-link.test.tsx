import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { UserTier } from "@/common/hooks/use-user-limits";
import { BillingSummaryLink } from "../billing-summary-link";

/**
 * Settings → General names the plan and links to Billing: the pricing page's
 * "Manage subscription" still lands on General, so this line is how a
 * subscriber reaches their plan in one click.
 */

const { mockUseUserLimits } = vi.hoisted(() => ({
  mockUseUserLimits: vi.fn(),
}));

vi.mock("@/common/hooks/use-user-limits", () => ({
  useUserLimits: () => mockUseUserLimits(),
}));

vi.mock("@tanstack/react-router", async () => {
  const { routerMock } = await import("@/test/mocks/router");
  return routerMock;
});

vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("BillingSummaryLink", () => {
  it.each([
    ["FREE", "userSettings.freePlan"],
    ["PREMIUM", "aiAgent.premiumTier"],
    ["GROWTH", "aiAgent.growthTier"],
    ["ENTERPRISE", "userSettings.enterprisePlan"],
  ] as const satisfies ReadonlyArray<readonly [UserTier, string]>)(
    "names the %s plan and links to Billing",
    (tier, planKey) => {
      mockUseUserLimits.mockReturnValue({ tier });

      render(<BillingSummaryLink />);

      expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(
        "userSettings.subscription",
      );
      expect(screen.getByText(planKey)).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: "userSettings.billing" }),
      ).toHaveAttribute("href", "/settings/billing");
    },
  );
});
