import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlanChangeSheet } from "../plan-change-sheet";
import { MOCK_TIER_QUOTAS } from "./subscription-test-utils";

const { mockRunPreview, mockChangePlan, mockPreview, mockTrack } = vi.hoisted(
  () => ({
    mockTrack: vi.fn(),
    mockRunPreview: vi.fn(),
    mockChangePlan: vi.fn(),
    mockPreview: {
      state: { data: undefined, loading: false, error: undefined } as {
        data: unknown;
        loading: boolean;
        error: unknown;
      },
    },
  }),
);

vi.mock("@/features/user-settings/hooks/use-plan-change", () => ({
  usePreviewPlanChange: () => [mockRunPreview, mockPreview.state],
  useChangePlan: () => [mockChangePlan, { loading: false }],
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/common/analytics", () => ({ track: mockTrack }));
vi.mock("@/common/lib/errors/error-message", () => ({
  useErrorMessage: () => () => "error",
}));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}));

const t = (key: string, params?: Record<string, string | number>) =>
  params ? `${key} ${Object.values(params).join(" ")}` : key;
const GROWTH_YEARLY = "price_1SyPdbEqsEqs2tLV7PJyWZed";
const quotaByUserTier = Object.fromEntries(
  MOCK_TIER_QUOTAS.map((quota) => [quota.tier, quota]),
);

function preview(overrides: Record<string, unknown> = {}) {
  return {
    previewPlanChange: {
      kind: "TO_YEARLY",
      refusal: null,
      effect: "IMMEDIATE",
      currentPriceId: "price_1RrSOGEqsEqs2tLVFnyB34qG",
      targetPriceId: GROWTH_YEARLY,
      currency: "usd",
      amountDueToday: 95_000,
      creditApplied: 999,
      nextAmount: 95_988,
      nextChargeAt: "2027-10-17T12:00:00Z",
      effectiveAt: "2026-10-17T12:00:00Z",
      prorationDate: 1792238400,
      alternativePriceId: null,
      limitChanges: [],
      paymentMethod: { brand: "visa", last4: "4242" },
      ...overrides,
    },
  };
}

function renderSheet(
  props: Partial<Parameters<typeof PlanChangeSheet>[0]> = {},
) {
  const handlers = {
    onClose: vi.fn(),
    onCheckout: vi.fn(),
    onManageBilling: vi.fn(),
    onChanged: vi.fn(),
  };
  render(
    <PlanChangeSheet
      target={{ tier: "growth", cycle: "yearly", surface: "settings_billing" }}
      currentTier="PREMIUM"
      currentCycle="monthly"
      currentPlanLabel="Premium · Monthly"
      quotaByUserTier={quotaByUserTier}
      t={t}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
}

beforeEach(() => {
  vi.clearAllMocks();
  mockPreview.state = { data: preview(), loading: false, error: undefined };
  // Like Apollo's lazy query: the promise resolves with the response.
  mockRunPreview.mockImplementation(async () => ({
    data: mockPreview.state.data,
  }));
});

describe("PlanChangeSheet", () => {
  it("previews the target price as soon as it opens", () => {
    renderSheet();
    expect(mockRunPreview).toHaveBeenCalledWith({
      variables: { clientId: "beancount-web-prod", priceId: GROWTH_YEARLY },
    });
  });

  it("shows the charge, the credit, the next charge, the card and what the plan adds", () => {
    renderSheet();

    expect(screen.getByText("$950.00")).toBeInTheDocument();
    expect(
      screen.getByText("userSettings.planChangeCredit $9.99"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/userSettings\.planChangeNext \$959\.88/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("userSettings.planChangeChargedTo visa •••• 4242"),
    ).toBeInTheDocument();
    // Premium → Growth adds ledgers, collaborators, tokens and automation.
    expect(
      screen.getByText("userSettings.featureAutomationIntegrations"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("userSettings.featureAutomaticBackups"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "userSettings.planChangePayAndSwitch $950.00",
      }),
    ).toBeInTheDocument();
  });

  it("hands a new subscription to Checkout instead of changing a plan", async () => {
    const user = userEvent.setup();
    mockPreview.state = {
      data: preview({ kind: "NEW", effect: "CHECKOUT", prorationDate: null }),
      loading: false,
      error: undefined,
    };
    const { onCheckout } = renderSheet({ currentTier: "FREE" });

    await user.click(
      screen.getByRole("button", {
        name: "userSettings.planChangeContinueToCheckout",
      }),
    );
    expect(onCheckout).toHaveBeenCalledWith({
      tier: "growth",
      cycle: "yearly",
      surface: "settings_billing",
    });
    expect(mockChangePlan).not.toHaveBeenCalled();
  });

  it.each([
    ["CURRENT_PLAN", "userSettings.planChangeRefusalCurrent"],
    ["SAME_TIER_AND_CYCLE", "userSettings.planChangeRefusalSameTier"],
    ["MULTIPLE_SUBSCRIPTIONS", "userSettings.planChangeRefusalMultiple"],
  ])("explains the %s refusal and offers no confirm", (refusal, message) => {
    mockPreview.state = {
      data: preview({ kind: null, effect: null, refusal }),
      loading: false,
      error: undefined,
    };
    renderSheet();

    expect(screen.getByText(message)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /planChangePayAndSwitch/ }),
    ).not.toBeInTheDocument();
  });

  it("offers a retry when the price cannot be loaded", async () => {
    const user = userEvent.setup();
    mockPreview.state = {
      data: undefined,
      loading: false,
      error: new Error("boom"),
    };
    renderSheet();

    expect(
      screen.getByText("userSettings.planChangePreviewFailed"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "common.tryAgain" }));
    expect(mockRunPreview).toHaveBeenCalledTimes(2);
  });

  it("ignores a stale preview for a different price", () => {
    mockPreview.state = {
      data: preview({ targetPriceId: "price_other" }),
      loading: false,
      error: undefined,
    };
    renderSheet();
    expect(
      screen.getByText("userSettings.planChangePreviewing"),
    ).toBeInTheDocument();
  });

  it("renders nothing when closed", () => {
    const { container } = render(
      <PlanChangeSheet
        target={null}
        currentTier="PREMIUM"
        currentCycle={null}
        currentPlanLabel=""
        quotaByUserTier={quotaByUserTier}
        t={t}
        onClose={vi.fn()}
        onCheckout={vi.fn()}
        onManageBilling={vi.fn()}
        onChanged={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
    expect(mockRunPreview).not.toHaveBeenCalled();
  });

  it("cannot confirm again while a Checkout is being created", () => {
    mockPreview.state = {
      data: preview({ kind: "NEW", effect: "CHECKOUT", prorationDate: null }),
      loading: false,
      error: undefined,
    };
    renderSheet({
      currentTier: "FREE",
      currentCycle: null,
      checkoutPending: true,
    });
    expect(
      screen.getByRole("button", {
        name: "userSettings.planChangeContinueToCheckout",
      }),
    ).toBeDisabled();
  });

  describe("analytics", () => {
    const CHANGE = {
      kind: "TO_YEARLY",
      from: "premium_monthly",
      to: "growth_yearly",
      surface: "settings_billing",
    };
    const events = (name: string) =>
      mockTrack.mock.calls.filter(([event]) => event === name);
    const sheet = () => (
      <PlanChangeSheet
        target={{
          tier: "growth",
          cycle: "yearly",
          surface: "settings_billing",
        }}
        currentTier="PREMIUM"
        currentCycle="monthly"
        currentPlanLabel="Premium · Monthly"
        quotaByUserTier={quotaByUserTier}
        t={t}
        onClose={vi.fn()}
        onCheckout={vi.fn()}
        onManageBilling={vi.fn()}
        onChanged={vi.fn()}
      />
    );

    it("reports each preview response once, with the plans and surface", async () => {
      const { rerender } = render(sheet());
      await waitFor(() =>
        expect(events("plan_change_previewed")).toEqual([
          ["plan_change_previewed", CHANGE],
        ]),
      );
      rerender(sheet());
      expect(mockRunPreview).toHaveBeenCalledTimes(1);
      expect(events("plan_change_previewed")).toHaveLength(1);
    });

    it("counts a retried preview again", async () => {
      const user = userEvent.setup();
      mockPreview.state = {
        data: undefined,
        loading: false,
        error: new Error("boom"),
      };
      renderSheet();
      mockRunPreview.mockResolvedValueOnce({ data: preview() });
      await user.click(screen.getByRole("button", { name: "common.tryAgain" }));
      await waitFor(() =>
        expect(events("plan_change_previewed")).toEqual([
          ["plan_change_previewed", CHANGE],
        ]),
      );
    });

    it("does not report a refused preview", async () => {
      mockPreview.state = {
        data: preview({ kind: null, refusal: "CURRENT_PLAN" }),
        loading: false,
        error: undefined,
      };
      renderSheet();
      await waitFor(() => expect(mockRunPreview).toHaveBeenCalled());
      await Promise.resolve();
      expect(events("plan_change_previewed")).toEqual([]);
    });

    it("names the tier alone without a current subscription", async () => {
      mockPreview.state = {
        data: preview({
          kind: "NEW",
          effect: "CHECKOUT",
          currentPriceId: null,
        }),
        loading: false,
        error: undefined,
      };
      renderSheet({ currentTier: "FREE", currentCycle: null });
      await waitFor(() =>
        expect(events("plan_change_previewed")[0]?.[1]).toMatchObject({
          kind: "NEW",
          from: "free",
        }),
      );
    });

    it.each([
      ["ACTIVE", { status: "ACTIVE" }, []],
      [
        "REQUIRES_ACTION",
        { status: "REQUIRES_ACTION", hostedInvoiceUrl: null },
        ["payment_action_required"],
      ],
      ["FAILED", { status: "FAILED" }, ["payment_action_failed"]],
      // No result is not a decline.
      ["missing", null, []],
    ])(
      "reports the confirm and a %s result",
      async (_label, changePlan, outcomeEvents) => {
        const user = userEvent.setup();
        mockChangePlan.mockResolvedValue({ data: { changePlan } });
        renderSheet();

        await user.click(
          screen.getByRole("button", {
            name: "userSettings.planChangePayAndSwitch $950.00",
          }),
        );

        expect(events("plan_change_confirmed")).toEqual([
          ["plan_change_confirmed", CHANGE],
        ]);
        expect(
          mockTrack.mock.calls
            .map(([event]) => event as string)
            .filter((event) => event.startsWith("payment_action")),
        ).toEqual(outcomeEvents);
      },
    );
  });
});
