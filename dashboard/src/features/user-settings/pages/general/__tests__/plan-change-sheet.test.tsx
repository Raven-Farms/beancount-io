import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlanChangeSheet } from "../plan-change-sheet";
import { MOCK_TIER_QUOTAS } from "./subscription-test-utils";

const { mockRunPreview, mockChangePlan, mockPreview } = vi.hoisted(() => ({
  mockRunPreview: vi.fn(),
  mockChangePlan: vi.fn(),
  mockPreview: {
    state: { data: undefined, loading: false, error: undefined } as {
      data: unknown;
      loading: boolean;
      error: unknown;
    },
  },
}));

vi.mock("@/features/user-settings/hooks/use-plan-change", () => ({
  usePreviewPlanChange: () => [mockRunPreview, mockPreview.state],
  useChangePlan: () => [mockChangePlan, { loading: false }],
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
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
      target={{ tier: "growth", cycle: "yearly" }}
      currentTier="PREMIUM"
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
});
