import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CancellationReason } from "@/graphql/definitions";
import { ScheduledPanel } from "../scheduled-panel";
import { CancelSheet } from "../cancel-sheet";
import {
  MOCK_TIER_QUOTAS,
  mockActiveSubscriptionData,
} from "./subscription-test-utils";

vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}));

const t = (key: string, params?: Record<string, string | number>) =>
  params ? `${key} ${Object.values(params).join(" ")}` : key;
const subscription =
  mockActiveSubscriptionData.subscriptionStatus.subscriptions[0];
const FREE = MOCK_TIER_QUOTAS.find((quota) => quota.tier === "FREE");

describe("ScheduledPanel", () => {
  const renderPanel = (overrides: Partial<typeof subscription>) => {
    const handlers = { onKeepCurrent: vi.fn(), onResume: vi.fn() };
    const { container } = render(
      <ScheduledPanel
        subscription={{ ...subscription, ...overrides }}
        currentName="Growth · Monthly"
        busy={false}
        t={t}
        {...handlers}
      />,
    );
    return { ...handlers, container };
  };

  it("renders nothing without a pending change", () => {
    const { container } = renderPanel({});
    expect(container).toBeEmptyDOMElement();
  });

  it("names a scheduled change and undoes it with Keep current", async () => {
    const user = userEvent.setup();
    const { onKeepCurrent, onResume } = renderPanel({
      scheduledChange: {
        __typename: "ScheduledPlanChange",
        priceId: "price_1RrSOGEqsEqs2tLVFnyB34qG",
        effectiveAt: "2026-11-03T12:00:00Z",
      },
    });

    expect(
      screen.getByText(
        /^userSettings\.scheduledChangesTo aiAgent\.premiumTier · userSettings\.monthly/,
      ),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "userSettings.scheduledKeepCurrent" }),
    );
    expect(onKeepCurrent).toHaveBeenCalledTimes(1);
    expect(onResume).not.toHaveBeenCalled();
  });

  it("says when a cancelled plan ends and offers Resume", async () => {
    const user = userEvent.setup();
    const { onResume } = renderPanel({
      cancelAtPeriodEnd: true,
      cancelAt: "2026-11-03T12:00:00Z",
    });

    expect(
      screen.getByText(/^userSettings\.scheduledEnds Growth · Monthly/),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "userSettings.resumeSubscription" }),
    );
    expect(onResume).toHaveBeenCalledTimes(1);
  });
});

describe("CancelSheet", () => {
  const renderSheet = (
    props: Partial<Parameters<typeof CancelSheet>[0]> = {},
  ) => {
    const handlers = {
      onConfirm: vi.fn(),
      onKeep: vi.fn(),
      onAlternative: vi.fn(),
    };
    render(
      <CancelSheet
        planName="Growth"
        tier="growth"
        cycle="monthly"
        endsAt="2026-11-03T12:00:00Z"
        freeQuota={FREE}
        busy={false}
        t={t}
        {...handlers}
        {...props}
      />,
    );
    return handlers;
  };

  it("says what is kept until when, the Free limits after, and that nothing is deleted", () => {
    renderSheet();
    expect(
      screen.getByText(/^userSettings\.cancelSheetKeepUntil Growth/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("userSettings.cancelSheetPlainText"),
    ).toBeInTheDocument();
  });

  it("offers yearly to a monthly plan", async () => {
    const user = userEvent.setup();
    const { onAlternative } = renderSheet({ tier: "growth", cycle: "monthly" });
    await user.click(
      screen.getByRole("button", {
        name: /^userSettings\.cancelSheetSwitchToYearly/,
      }),
    );
    expect(onAlternative).toHaveBeenCalledWith({
      tier: "growth",
      cycle: "yearly",
    });
  });

  it("offers the next tier down to a yearly plan from Growth up", async () => {
    const user = userEvent.setup();
    const { onAlternative } = renderSheet({ tier: "growth", cycle: "yearly" });
    await user.click(
      screen.getByRole("button", {
        name: /^userSettings\.cancelSheetDowngradeTo aiAgent\.premiumTier/,
      }),
    );
    expect(onAlternative).toHaveBeenCalledWith({
      tier: "premium",
      cycle: "yearly",
    });
  });

  it("offers no alternative to Premium on yearly", () => {
    renderSheet({ tier: "premium", cycle: "yearly" });
    expect(
      screen.queryByText("userSettings.cancelSheetOtherOptions"),
    ).not.toBeInTheDocument();
  });

  it("confirms with the optional reason, or none", async () => {
    const user = userEvent.setup();
    const { onConfirm } = renderSheet();
    await user.click(
      screen.getByRole("radio", { name: "userSettings.cancelReasonUnused" }),
    );
    await user.click(
      screen.getByRole("button", { name: "userSettings.cancelSubscription" }),
    );
    expect(onConfirm).toHaveBeenCalledWith(CancellationReason.Unused);
  });

  it("gives Cancel and Keep the same weight", () => {
    renderSheet();
    const cancel = screen.getByRole("button", {
      name: "userSettings.cancelSubscription",
    });
    const keep = screen.getByRole("button", {
      name: /^userSettings\.planChangeKeep/,
    });
    expect(cancel.className).toBe(keep.className);
  });

  it("cannot be left while the cancellation is being sent", () => {
    const { onKeep } = renderSheet({ busy: true });
    expect(
      screen.getByRole("button", { name: /^userSettings\.planChangeKeep/ }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", {
        name: /^userSettings\.cancelSheetSwitchToYearly/,
      }),
    ).toBeDisabled();
    expect(onKeep).not.toHaveBeenCalled();
  });
});
