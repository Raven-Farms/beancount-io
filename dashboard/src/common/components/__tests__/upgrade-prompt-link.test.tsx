import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { UpgradePromptLink } from "../upgrade-prompt-link";
import { getNextTier } from "@/common/lib/subscription/tier-config";
import { TEST_LOCATION_HREF } from "@/test/mocks/router";

const { mockTrack } = vi.hoisted(() => ({ mockTrack: vi.fn() }));

vi.mock("@tanstack/react-router", async () => {
  const { routerMock } = await import("@/test/mocks/router");
  return routerMock;
});
vi.mock("@/common/analytics", () => ({ track: mockTrack }));

describe("UpgradePromptLink", () => {
  beforeEach(() => mockTrack.mockClear());

  it("opens the recommended plan with the way back and records it", () => {
    render(
      <UpgradePromptLink surface="ledgers_limit" plan={getNextTier("PREMIUM")}>
        Upgrade
      </UpgradePromptLink>,
    );

    const link = screen.getByRole("link", { name: "Upgrade" });
    expect(link).toHaveAttribute(
      "href",
      `/settings/billing?plan=growth&billing=yearly&from=ledgers_limit&return=${encodeURIComponent(TEST_LOCATION_HREF)}`,
    );
    fireEvent.click(link);
    expect(mockTrack).toHaveBeenCalledWith("upgrade_prompt_clicked", {
      surface: "ledgers_limit",
      target_tier: "GROWTH",
    });
  });

  it("opens Billing without a plan when none is above", () => {
    render(
      <UpgradePromptLink
        surface="collaborators_limit"
        plan={getNextTier("ORGANIZATION")}
      >
        Upgrade
      </UpgradePromptLink>,
    );

    const link = screen.getByRole("link", { name: "Upgrade" });
    expect(link).toHaveAttribute(
      "href",
      `/settings/billing?from=collaborators_limit&return=${encodeURIComponent(TEST_LOCATION_HREF)}`,
    );
    fireEvent.click(link);
    expect(mockTrack).toHaveBeenCalledWith("upgrade_prompt_clicked", {
      surface: "collaborators_limit",
    });
  });
});
