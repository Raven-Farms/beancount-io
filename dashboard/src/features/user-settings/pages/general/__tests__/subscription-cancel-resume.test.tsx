import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SubscriptionSection } from "../subscription-section";
import {
  MOCK_TIER_QUOTAS,
  mockActiveSubscriptionData,
  mockCanceledSubscriptionData,
} from "./subscription-test-utils";

const {
  mockUseQuery,
  mockCancelSubscription,
  mockResumeSubscription,
  mockCreateStripePortalSession,
  mockCreateSubscriptionSession,
  mockUpgradeSubscription,
  mockToastSuccess,
  mockToastError,
  mockToastInfo,
  mockUseUserLimits,
  mockUseAiCfoUsage,
  mockUseAllTierQuotas,
  mockTrack,
  mockCancelScheduled,
} = vi.hoisted(() => ({
  mockUseQuery: vi.fn(),
  mockCancelSubscription: vi.fn(),
  mockResumeSubscription: vi.fn(),
  mockCreateStripePortalSession: vi.fn(),
  mockCreateSubscriptionSession: vi.fn(),
  mockUpgradeSubscription: vi.fn(),
  mockToastSuccess: vi.fn(),
  mockToastError: vi.fn(),
  mockToastInfo: vi.fn(),
  mockUseUserLimits: vi.fn(),
  mockUseAiCfoUsage: vi.fn(),
  mockUseAllTierQuotas: vi.fn(),
  mockTrack: vi.fn(),
  mockCancelScheduled: vi.fn(),
}));

vi.mock("@/common/analytics", () => ({ track: mockTrack }));

vi.mock("@apollo/client/react", () => ({
  useLazyQuery: () => [
    vi.fn(),
    { data: undefined, loading: false, error: undefined },
  ],
  useQuery: () => mockUseQuery(),
  useMutation: (document: {
    definitions?: Array<{ name?: { value?: string } }>;
  }) => {
    const opName = document?.definitions?.[0]?.name?.value;
    if (opName === "CancelSubscription")
      return [mockCancelSubscription, { loading: false }];
    if (opName === "ResumeSubscription")
      return [mockResumeSubscription, { loading: false }];
    if (opName === "CreateStripePortalSession")
      return [mockCreateStripePortalSession, { loading: false }];
    if (opName === "CancelScheduledPlanChange")
      return [mockCancelScheduled, { loading: false }];
    return [vi.fn(), { loading: false }];
  },
}));

vi.mock("@/common/hooks/use-user-limits", () => ({
  useUserLimits: () => mockUseUserLimits(),
}));
vi.mock("@/common/hooks/use-ai-cfo-usage", () => ({
  useAiCfoUsage: () => mockUseAiCfoUsage(),
}));
vi.mock("@/common/hooks/use-all-tier-quotas", () => ({
  useAllTierQuotas: () => mockUseAllTierQuotas(),
}));
vi.mock(
  "@/features/user-settings/hooks/use-create-subscription-session",
  () => ({
    useCreateSubscriptionSession: () => ({
      createSubscriptionSession: mockCreateSubscriptionSession,
      loading: false,
    }),
  }),
);
vi.mock("@/features/user-settings/hooks/use-upgrade-subscription", () => ({
  useUpgradeSubscription: () => ({
    upgradeSubscription: mockUpgradeSubscription,
    loading: false,
  }),
}));
vi.mock("sonner", () => ({
  toast: {
    success: mockToastSuccess,
    error: mockToastError,
    info: mockToastInfo,
  },
}));

vi.mock("@/common/components/ui/card", () => ({
  Card: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card">{children}</div>
  ),
  CardContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card-content">{children}</div>
  ),
  CardDescription: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card-description">{children}</div>
  ),
  CardHeader: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card-header">{children}</div>
  ),
  CardTitle: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card-title">{children}</div>
  ),
}));
vi.mock("@/common/components/ui/button", () => ({
  Button: ({
    children,
    onClick,
    disabled,
    ...props
  }: {
    children?: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    [key: string]: unknown;
  }) => (
    <button onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  ),
}));
vi.mock("@/common/components/ui/badge", () => ({
  Badge: ({
    children,
    ...props
  }: {
    children?: React.ReactNode;
    [key: string]: unknown;
  }) => <span {...props}>{children}</span>,
}));
vi.mock("@/common/components/ui/dialog", () => ({
  Dialog: ({
    children,
    open,
  }: {
    children: React.ReactNode;
    open?: boolean;
  }) => (
    <div data-testid="dialog" data-open={open}>
      {children}
    </div>
  ),
  DialogContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dialog-content">{children}</div>
  ),
  DialogDescription: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dialog-description">{children}</div>
  ),
  DialogFooter: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dialog-footer">{children}</div>
  ),
  DialogHeader: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dialog-header">{children}</div>
  ),
  DialogTitle: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dialog-title">{children}</div>
  ),
}));
vi.mock("@/common/components/ui/separator", () => ({
  Separator: () => <hr data-testid="separator" />,
}));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({
    t: (key: string, params?: Record<string, string>) => {
      if (params) {
        let result = key;
        for (const [k, v] of Object.entries(params))
          result = result.replace(`{${k}}`, v);
        if (result === key) return key;
        return result;
      }
      return key;
    },
    // The app-locale number formatter reads `i18n.language`.
    i18n: { language: "en" },
  }),
}));

function setUserLimits(
  tier = "FREE" as string,
  limits: {
    aiCfoTokensUsed?: number;
    aiCfoTokensMax?: number;
    ledgersUsed?: number;
    ledgersMax?: number;
    collaboratorsPerLedgerMax?: number;
  } = {},
) {
  const {
    aiCfoTokensUsed = 5,
    aiCfoTokensMax = 10,
    ledgersUsed = 1,
    ledgersMax = 3,
    collaboratorsPerLedgerMax = 3,
  } = limits;
  mockUseUserLimits.mockReturnValue({
    tier,
    limits: { ledgersUsed, ledgersMax, collaboratorsPerLedgerMax },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    isAtLedgerLimit: false,
    isPremium: tier === "PREMIUM",
    isFree: tier === "FREE",
    isGrowth: tier === "GROWTH",
    isOrganization: tier === "ORGANIZATION",
    isEnterprise: tier === "ENTERPRISE",
    isPaidTier: tier !== "FREE",
  });
  mockUseAiCfoUsage.mockReturnValue({
    aiCfoTokensUsed,
    aiCfoTokensMax,
    isAtAiCfoLimit: aiCfoTokensMax !== -1 && aiCfoTokensUsed >= aiCfoTokensMax,
    isLoading: false,
    error: undefined,
    usage: { aiCfoTokensUsed, aiCfoTokensMax },
    refetch: vi.fn(),
  });
  mockUseAllTierQuotas.mockReturnValue({
    quotas: MOCK_TIER_QUOTAS,
    getQuotaForTier: (t: string) =>
      MOCK_TIER_QUOTAS.find((q) => q.tier === t) ?? null,
    isLoading: false,
    error: undefined,
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  setUserLimits();
});

/** The open cancel sheet; the dialog mock drops its test id. */
function cancelSheet(): HTMLElement {
  const sheet = screen
    .getByText("userSettings.cancelSheetTitle")
    .closest<HTMLElement>('[data-testid="dialog-content"]');
  if (!sheet) throw new Error("cancel sheet missing");
  return sheet;
}

describe("Cancel Subscription Functionality", () => {
  it("should open cancel dialog when cancel button clicked", async () => {
    const user = userEvent.setup();
    setUserLimits("PREMIUM", {
      aiCfoTokensUsed: 50,
      aiCfoTokensMax: 100,
      ledgersUsed: 2,
      ledgersMax: 5,
      collaboratorsPerLedgerMax: 5,
    });
    mockUseQuery.mockReturnValue({
      data: mockActiveSubscriptionData,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<SubscriptionSection />);

    const cancelButton = screen.getByText("userSettings.cancelSubscription");
    await user.click(cancelButton);

    await waitFor(() => {
      expect(
        screen.getByText("userSettings.cancelSheetTitle"),
      ).toBeInTheDocument();
    });
  });

  it("should handle cancel error", async () => {
    const user = userEvent.setup();
    setUserLimits("PREMIUM", {
      aiCfoTokensUsed: 50,
      aiCfoTokensMax: 100,
      ledgersUsed: 2,
      ledgersMax: 5,
      collaboratorsPerLedgerMax: 5,
    });
    mockUseQuery.mockReturnValue({
      data: mockActiveSubscriptionData,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    mockCancelSubscription.mockRejectedValue(new Error("Cancel failed"));

    render(<SubscriptionSection />);

    const cancelButton = screen.getByText("userSettings.cancelSubscription");
    await user.click(cancelButton);

    await waitFor(() => {
      expect(
        within(cancelSheet()).getByText("userSettings.cancelSubscription"),
      ).toBeInTheDocument();
    });

    const confirmButton = within(cancelSheet()).getByText(
      "userSettings.cancelSubscription",
    );
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalled();
    });
  });

  it("should close dialog on cancel button click", async () => {
    const user = userEvent.setup();
    setUserLimits("PREMIUM", {
      aiCfoTokensUsed: 50,
      aiCfoTokensMax: 100,
      ledgersUsed: 2,
      ledgersMax: 5,
      collaboratorsPerLedgerMax: 5,
    });
    mockUseQuery.mockReturnValue({
      data: mockActiveSubscriptionData,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<SubscriptionSection />);

    const cancelButton = screen.getByText("userSettings.cancelSubscription");
    await user.click(cancelButton);

    await waitFor(() => {
      expect(
        screen.getByText("userSettings.cancelSheetTitle"),
      ).toBeInTheDocument();
    });

    await user.click(
      within(cancelSheet()).getByText("userSettings.planChangeKeep"),
    );

    await waitFor(() => {
      expect(
        screen.queryByText("userSettings.cancelSheetTitle"),
      ).not.toBeInTheDocument();
    });
    expect(mockCancelSubscription).not.toHaveBeenCalled();
  });
});

describe("Resume Subscription Functionality", () => {
  it("should resume subscription and show success toast", async () => {
    const user = userEvent.setup();
    const mockRefetch = vi.fn();
    setUserLimits("PREMIUM", {
      aiCfoTokensUsed: 50,
      aiCfoTokensMax: 100,
      ledgersUsed: 2,
      ledgersMax: 5,
      collaboratorsPerLedgerMax: 5,
    });
    mockUseQuery.mockReturnValue({
      data: mockCanceledSubscriptionData,
      loading: false,
      error: null,
      refetch: mockRefetch,
    });

    mockResumeSubscription.mockResolvedValue({
      data: {
        resumeSubscription: {
          success: true,
          message: "Subscription resumed successfully.",
        },
      },
    });

    render(<SubscriptionSection />);

    const resumeButton = screen.getByText("userSettings.resumeSubscription");
    await user.click(resumeButton);

    await waitFor(() => {
      expect(
        screen.getByText("userSettings.resumeSubscriptionTitle"),
      ).toBeInTheDocument();
    });

    const confirmButton = screen.getByText("userSettings.confirmResume");
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockResumeSubscription).toHaveBeenCalledWith({
        variables: { subscriptionId: "sub_456", clientId: "test-client" },
      });
      expect(mockToastSuccess).toHaveBeenCalled();
      // Status refetches through the mutation's refetchQueries.
    });
  });

  it("should handle resume error", async () => {
    const user = userEvent.setup();
    setUserLimits("PREMIUM", {
      aiCfoTokensUsed: 50,
      aiCfoTokensMax: 100,
      ledgersUsed: 2,
      ledgersMax: 5,
      collaboratorsPerLedgerMax: 5,
    });
    mockUseQuery.mockReturnValue({
      data: mockCanceledSubscriptionData,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    mockResumeSubscription.mockRejectedValue(new Error("Resume failed"));

    render(<SubscriptionSection />);

    const resumeButton = screen.getByText("userSettings.resumeSubscription");
    await user.click(resumeButton);

    await waitFor(() => {
      expect(
        screen.getByText("userSettings.confirmResume"),
      ).toBeInTheDocument();
    });

    const confirmButton = screen.getByText("userSettings.confirmResume");
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalled();
    });
  });
});

describe("Cancel Subscription - Success Flow", () => {
  it("should call cancelSubscription and refetch on successful cancel", async () => {
    const user = userEvent.setup();
    const mockRefetch = vi.fn();
    setUserLimits("PREMIUM", {
      aiCfoTokensUsed: 50,
      aiCfoTokensMax: 100,
      ledgersUsed: 2,
      ledgersMax: 5,
      collaboratorsPerLedgerMax: 5,
    });
    mockUseQuery.mockReturnValue({
      data: mockActiveSubscriptionData,
      loading: false,
      error: null,
      refetch: mockRefetch,
    });

    mockCancelSubscription.mockResolvedValue({
      data: {
        cancelSubscription: {
          success: true,
        },
      },
    });

    render(<SubscriptionSection />);

    // Open cancel dialog
    const cancelButton = screen.getByText("userSettings.cancelSubscription");
    await user.click(cancelButton);

    await waitFor(() => {
      expect(
        within(cancelSheet()).getByText("userSettings.cancelSubscription"),
      ).toBeInTheDocument();
    });

    // Confirm cancellation
    const confirmButton = within(cancelSheet()).getByText(
      "userSettings.cancelSubscription",
    );
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockCancelSubscription).toHaveBeenCalledWith({
        variables: {
          subscriptionId: "sub_123",
          clientId: "test-client",
          reason: null,
        },
      });
    });

    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith(
        "userSettings.subscriptionCanceledSuccess",
      );
    });

    await waitFor(() => {
      // Status refetches through the mutation's refetchQueries.
    });
  });

  it("should show error toast when cancel returns failure", async () => {
    const user = userEvent.setup();
    setUserLimits("PREMIUM", {
      aiCfoTokensUsed: 50,
      aiCfoTokensMax: 100,
      ledgersUsed: 2,
      ledgersMax: 5,
      collaboratorsPerLedgerMax: 5,
    });
    mockUseQuery.mockReturnValue({
      data: mockActiveSubscriptionData,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    mockCancelSubscription.mockResolvedValue({
      data: {
        cancelSubscription: {
          success: false,
          message: "Subscription not found",
        },
      },
    });

    render(<SubscriptionSection />);

    const cancelButton = screen.getByText("userSettings.cancelSubscription");
    await user.click(cancelButton);

    await waitFor(() => {
      expect(
        within(cancelSheet()).getByText("userSettings.cancelSubscription"),
      ).toBeInTheDocument();
    });

    const confirmButton = within(cancelSheet()).getByText(
      "userSettings.cancelSubscription",
    );
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Subscription not found");
    });
  });
});

describe("Billing lifecycle events", () => {
  const events = (name: string) =>
    mockTrack.mock.calls.filter(([event]) => event === name);

  beforeEach(() => {
    mockTrack.mockClear();
    setUserLimits("PREMIUM", {
      aiCfoTokensUsed: 50,
      aiCfoTokensMax: 100,
      ledgersUsed: 2,
      ledgersMax: 5,
      collaboratorsPerLedgerMax: 5,
    });
  });

  it("reports the cancel sheet opening once, and the cancellation with its reason once", async () => {
    const user = userEvent.setup();
    mockUseQuery.mockReturnValue({
      data: mockActiveSubscriptionData,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    mockCancelSubscription.mockResolvedValue({
      data: { cancelSubscription: { success: true } },
    });

    render(<SubscriptionSection />);
    await user.click(screen.getByText("userSettings.cancelSubscription"));
    expect(events("cancel_started")).toHaveLength(1);

    await user.click(
      within(cancelSheet()).getByRole("radio", {
        name: "userSettings.cancelReasonTooExpensive",
      }),
    );
    await user.click(
      within(cancelSheet()).getByText("userSettings.cancelSubscription"),
    );

    await waitFor(() =>
      expect(events("cancel_confirmed")).toEqual([
        [
          "cancel_confirmed",
          expect.objectContaining({ reason: "too_expensive" }),
        ],
      ]),
    );
    expect(mockCancelSubscription).toHaveBeenCalledWith({
      variables: expect.objectContaining({ reason: "TOO_EXPENSIVE" }),
    });
  });

  it("reports no cancellation when Stripe refuses it", async () => {
    const user = userEvent.setup();
    mockUseQuery.mockReturnValue({
      data: mockActiveSubscriptionData,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    mockCancelSubscription.mockResolvedValue({
      data: { cancelSubscription: { success: false, message: "no" } },
    });

    render(<SubscriptionSection />);
    await user.click(screen.getByText("userSettings.cancelSubscription"));
    await user.click(
      within(cancelSheet()).getByText("userSettings.cancelSubscription"),
    );

    await waitFor(() => expect(mockToastError).toHaveBeenCalled());
    expect(events("cancel_confirmed")).toEqual([]);
  });

  it("reports a resume once it succeeds", async () => {
    const user = userEvent.setup();
    mockUseQuery.mockReturnValue({
      data: mockCanceledSubscriptionData,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    mockResumeSubscription.mockResolvedValue({
      data: { resumeSubscription: { success: true } },
    });

    render(<SubscriptionSection />);
    await user.click(screen.getByText("userSettings.resumeSubscription"));
    await user.click(screen.getByText("userSettings.confirmResume"));

    await waitFor(() => expect(events("subscription_resumed")).toHaveLength(1));
  });

  it("undoes a scheduled change from the Scheduled panel and reports it", async () => {
    const user = userEvent.setup();
    const scheduled = structuredClone(mockActiveSubscriptionData);
    scheduled.subscriptionStatus.subscriptions[0].scheduledChange = {
      __typename: "ScheduledPlanChange",
      priceId: "price_1RrSOGEqsEqs2tLVFnyB34qG",
      effectiveAt: "2026-11-03T12:00:00Z",
    };
    mockUseQuery.mockReturnValue({
      data: scheduled,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    mockCancelScheduled.mockResolvedValue({
      data: { cancelScheduledPlanChange: { success: true } },
    });

    render(<SubscriptionSection />);
    await user.click(screen.getByText("userSettings.scheduledKeepCurrent"));

    expect(mockCancelScheduled).toHaveBeenCalledWith({
      variables: { clientId: "beancount-web-prod" },
    });
    await waitFor(() =>
      expect(events("plan_change_reverted")).toEqual([
        [
          "plan_change_reverted",
          expect.objectContaining({ to: "premium_monthly" }),
        ],
      ]),
    );
    expect(mockToastSuccess).toHaveBeenCalledWith("userSettings.scheduledKept");
  });
});
