import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SubscriptionSection } from "../subscription-section";
import {
  MOCK_TIER_QUOTAS,
  mockActiveSubscriptionData,
  mockNoSubscriptionData,
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
}));

vi.mock("@apollo/client/react", () => ({
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

const PRICES = {
  premiumMonthly: "price_1RrSOGEqsEqs2tLVFnyB34qG",
  premiumYearly: "price_1L9ccEEqsEqs2tLVbeBgHm9p",
  growthMonthly: "price_1SyPdaEqsEqs2tLViLPUDoVi",
  growthYearly: "price_1SyPdbEqsEqs2tLV7PJyWZed",
};

const card = (tier: string) => within(screen.getByTestId(`plan-card-${tier}`));

function showSubscription(data = mockActiveSubscriptionData) {
  mockUseQuery.mockReturnValue({
    data,
    loading: false,
    error: null,
    refetch: vi.fn(),
  });
}

function premiumSubscriber() {
  setUserLimits("PREMIUM", {
    aiCfoTokensUsed: 50,
    aiCfoTokensMax: 100,
    ledgersUsed: 2,
    ledgersMax: 5,
    collaboratorsPerLedgerMax: 5,
  });
  // The fixture subscription bills monthly.
  showSubscription(mockActiveSubscriptionData);
}

beforeEach(() => {
  Object.defineProperty(window, "location", {
    value: { href: "", search: "" },
    writable: true,
    configurable: true,
  });
});

describe("Plan row", () => {
  it("shows every tier on yearly billing by default, with Growth as most popular", () => {
    setUserLimits("FREE");
    showSubscription(mockNoSubscriptionData);

    render(<SubscriptionSection />);

    for (const tier of [
      "FREE",
      "PREMIUM",
      "GROWTH",
      "ORGANIZATION",
      "ENTERPRISE",
    ]) {
      expect(screen.getByTestId(`plan-card-${tier}`)).toBeInTheDocument();
    }
    expect(
      screen.getByRole("button", { name: "userSettings.yearly" }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(card("GROWTH").getByText("aiAgent.popular")).toBeInTheDocument();
    expect(
      card("PREMIUM").queryByText("aiAgent.popular"),
    ).not.toBeInTheDocument();
    expect(
      card("PREMIUM").getByText("userSettings.billedYearly"),
    ).toBeInTheDocument();
  });

  it("offers a free user every paid tier and keeps Free as the current plan", () => {
    setUserLimits("FREE");
    showSubscription(mockNoSubscriptionData);

    render(<SubscriptionSection />);

    for (const tier of ["PREMIUM", "GROWTH", "ORGANIZATION"]) {
      expect(
        card(tier).getByRole("button", { name: "aiAgent.upgradeCta" }),
      ).toBeEnabled();
    }
    expect(
      card("FREE").getByRole("button", { name: "userSettings.currentPlan" }),
    ).toBeDisabled();
    expect(
      card("ENTERPRISE").getByRole("link", { name: "userSettings.contactUs" }),
    ).toHaveAttribute("href", "https://beancount.io/tg");
  });

  it("checks a free user out on the cycle they chose", async () => {
    const user = userEvent.setup();
    setUserLimits("FREE");
    showSubscription(mockNoSubscriptionData);
    mockCreateSubscriptionSession.mockResolvedValue({
      data: {
        createSubscriptionSession: {
          success: true,
          sessionUrl: "https://checkout.stripe.com/session/test",
        },
      },
    });

    render(<SubscriptionSection />);
    await user.click(
      card("PREMIUM").getByRole("button", { name: "aiAgent.upgradeCta" }),
    );

    await waitFor(() => {
      expect(mockCreateSubscriptionSession).toHaveBeenCalledWith({
        variables: {
          clientId: "beancount-web-prod",
          priceId: PRICES.premiumYearly,
        },
      });
    });
    expect(window.location.href).toBe(
      "https://checkout.stripe.com/session/test",
    );

    await user.click(
      screen.getByRole("button", { name: "userSettings.monthly" }),
    );
    await user.click(
      card("GROWTH").getByRole("button", { name: "aiAgent.upgradeCta" }),
    );
    await waitFor(() => {
      expect(mockCreateSubscriptionSession).toHaveBeenLastCalledWith({
        variables: {
          clientId: "beancount-web-prod",
          priceId: PRICES.growthMonthly,
        },
      });
    });
  });

  it("labels each choice for a monthly subscriber the way the server classifies it", async () => {
    const user = userEvent.setup();
    premiumSubscriber();

    render(<SubscriptionSection />);

    // Yearly: every paid tier from Premium monthly is a switch to yearly.
    expect(
      card("PREMIUM").getByRole("button", {
        name: "userSettings.switchToYearly",
      }),
    ).toBeEnabled();
    expect(
      card("GROWTH").getByRole("button", {
        name: "userSettings.switchToYearly",
      }),
    ).toBeEnabled();
    // Free is a downgrade, which waits for the renewal date and is not live yet.
    expect(
      card("FREE").getByRole("button", { name: "userSettings.downgrade" }),
    ).toBeDisabled();

    await user.click(
      screen.getByRole("button", { name: "userSettings.monthly" }),
    );
    expect(
      card("PREMIUM").getByRole("button", { name: "userSettings.currentPlan" }),
    ).toBeDisabled();
    expect(
      card("GROWTH").getByRole("button", { name: "aiAgent.upgradeCta" }),
    ).toBeEnabled();
  });

  it("changes a subscriber's plan in place instead of opening a second checkout", async () => {
    const user = userEvent.setup();
    premiumSubscriber();
    mockUpgradeSubscription.mockResolvedValue({
      data: {
        upgradeSubscription: {
          success: true,
          message: "Subscription upgraded successfully.",
        },
      },
    });

    render(<SubscriptionSection />);
    await user.click(
      card("GROWTH").getByRole("button", {
        name: "userSettings.switchToYearly",
      }),
    );

    await waitFor(() => {
      expect(mockUpgradeSubscription).toHaveBeenCalledWith({
        variables: {
          clientId: "beancount-web-prod",
          priceId: PRICES.growthYearly,
        },
      });
    });
    expect(mockCreateSubscriptionSession).not.toHaveBeenCalled();
  });

  it("keeps a higher tier that would leave yearly billing for later", async () => {
    const user = userEvent.setup();
    setUserLimits("GROWTH", {
      aiCfoTokensUsed: 200,
      aiCfoTokensMax: 500,
      ledgersUsed: 5,
      ledgersMax: 20,
      collaboratorsPerLedgerMax: 10,
    });
    const yearly = structuredClone(mockActiveSubscriptionData);
    yearly.subscriptionStatus.subscriptions[0].items[0].price.interval = "year";
    showSubscription(yearly);

    render(<SubscriptionSection />);
    await user.click(
      screen.getByRole("button", { name: "userSettings.monthly" }),
    );

    expect(
      card("ORGANIZATION").getByRole("button", { name: "aiAgent.upgradeCta" }),
    ).toBeDisabled();
    expect(
      card("GROWTH").getByRole("button", {
        name: "userSettings.switchToMonthly",
      }),
    ).toBeDisabled();
    expect(
      card("ORGANIZATION").getByText("userSettings.renewalChangesComingSoon"),
    ).toBeInTheDocument();
  });

  it("shows checkout errors to a free user", async () => {
    const user = userEvent.setup();
    setUserLimits("FREE");
    showSubscription(mockNoSubscriptionData);
    mockCreateSubscriptionSession
      .mockResolvedValueOnce({
        data: {
          createSubscriptionSession: {
            success: false,
            sessionUrl: null,
            message: "Card declined",
          },
        },
      })
      .mockRejectedValueOnce(new Error("Network failure"));

    render(<SubscriptionSection />);
    const premium = card("PREMIUM").getByRole("button", {
      name: "aiAgent.upgradeCta",
    });
    await user.click(premium);
    await waitFor(() =>
      expect(mockToastError).toHaveBeenCalledWith("Card declined"),
    );
    await user.click(premium);
    await waitFor(() =>
      expect(mockToastError).toHaveBeenLastCalledWith("common.errors.generic"),
    );
  });
});

describe("Pay yearly offer", () => {
  it("offers a monthly subscriber their plan on yearly billing and switches it in place", async () => {
    const user = userEvent.setup();
    premiumSubscriber();
    mockUpgradeSubscription.mockResolvedValue({
      data: { upgradeSubscription: { success: true, message: "ok" } },
    });

    render(<SubscriptionSection />);
    const offer = within(screen.getByTestId("pay-yearly-offer"));
    expect(offer.getByText("userSettings.payYearlyOffer")).toBeInTheDocument();
    await user.click(
      offer.getByRole("button", { name: "userSettings.switchToYearly" }),
    );

    await waitFor(() => {
      expect(mockUpgradeSubscription).toHaveBeenCalledWith({
        variables: {
          clientId: "beancount-web-prod",
          priceId: PRICES.premiumYearly,
        },
      });
    });
  });

  it("is absent for a free user and for a yearly subscriber", () => {
    setUserLimits("FREE");
    showSubscription(mockNoSubscriptionData);
    const { unmount } = render(<SubscriptionSection />);
    expect(screen.queryByTestId("pay-yearly-offer")).not.toBeInTheDocument();
    unmount();

    premiumSubscriber();
    const yearly = structuredClone(mockActiveSubscriptionData);
    yearly.subscriptionStatus.subscriptions[0].items[0].price.interval = "year";
    showSubscription(yearly);
    render(<SubscriptionSection />);
    expect(screen.queryByTestId("pay-yearly-offer")).not.toBeInTheDocument();
  });
});
