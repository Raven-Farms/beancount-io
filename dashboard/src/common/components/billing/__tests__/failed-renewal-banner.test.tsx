import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FailedRenewalBanner } from "../failed-renewal-banner";

const { mockUseQuery, mockOpenPortal, mockNative, mockRoot } = vi.hoisted(
  () => ({
    mockUseQuery: vi.fn(),
    mockOpenPortal: vi.fn(),
    mockNative: { isReactNative: false },
    mockRoot: {
      userProfile: { tier: "PREMIUM" } as { tier: string } | null,
    },
  }),
);

vi.mock("@apollo/client/react", () => ({
  useQuery: (...args: unknown[]) => mockUseQuery(...args),
  useMutation: () => [mockOpenPortal, { loading: false }],
}));
vi.mock(
  "@/common/providers/react-native-bridge-provider/react-native-bridge-context",
  () => ({ useReactNativeContext: () => mockNative }),
);
vi.mock("@/common/hooks/use-root-context", () => ({
  useRootContext: () => mockRoot,
}));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({
    t: (key: string, params?: Record<string, string>) =>
      params ? `${key} ${Object.values(params).join(" | ")}` : key,
    i18n: { language: "en" },
  }),
}));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

const RETRY = "2026-10-24T12:00:00Z";
function subscription(overrides: Record<string, unknown> = {}) {
  return {
    status: "past_due",
    clientId: "beancount-web-prod",
    nextPaymentAttempt: RETRY,
    paymentMethod: { brand: "visa", last4: "4242" },
    items: [{ price: { id: "price_1RrSOGEqsEqs2tLVFnyB34qG" }, product: null }],
    ...overrides,
  };
}
const status = (...subscriptions: unknown[]) =>
  mockUseQuery.mockReturnValue({
    data: { subscriptionStatus: { subscriptions } },
  });

beforeEach(() => {
  vi.clearAllMocks();
  window.sessionStorage.clear();
  mockNative.isReactNative = false;
  mockRoot.userProfile = { tier: "PREMIUM" };
});

describe("FailedRenewalBanner", () => {
  it("names the card, the plan and the retry date while a renewal is past due", () => {
    status(subscription());
    render(<FailedRenewalBanner />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "common.failedRenewal visa •••• 4242 | aiAgent.premiumTier | Oct 24, 2026",
    );
  });

  it.each([
    ["an active subscription", subscription({ status: "active" })],
    [
      "a past-due one Stripe stopped retrying",
      subscription({ nextPaymentAttempt: null }),
    ],
  ])("stays hidden for %s", (_label, sub) => {
    status(sub);
    const { container } = render(<FailedRenewalBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it("opens the billing portal to update the card", async () => {
    const user = userEvent.setup();
    status(subscription());
    mockOpenPortal.mockResolvedValue({
      data: { createStripePortalSession: { success: true, sessionUrl: null } },
    });
    render(<FailedRenewalBanner />);

    await user.click(
      screen.getByRole("button", { name: "common.failedRenewalUpdate" }),
    );
    expect(mockOpenPortal).toHaveBeenCalledWith({
      variables: { clientId: "beancount-web-prod" },
    });
  });

  it("stays dismissed for the rest of the browser session", async () => {
    const user = userEvent.setup();
    status(subscription());
    const { unmount } = render(<FailedRenewalBanner />);

    await user.click(
      screen.getByRole("button", { name: "common.failedRenewalDismiss" }),
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    unmount();

    render(<FailedRenewalBanner />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it.each([
    ["a Free user", { tier: "FREE" }],
    ["a signed-out visitor", null],
  ])("never asks for the subscription status for %s", (_label, profile) => {
    mockRoot.userProfile = profile;
    status(subscription());
    const { container } = render(<FailedRenewalBanner />);

    expect(container).toBeEmptyDOMElement();
    expect(mockUseQuery).toHaveBeenCalledWith(expect.anything(), {
      skip: true,
    });
  });

  it("reads the shared status query, skipped in the native app's web view", () => {
    mockNative.isReactNative = true;
    status(subscription());
    const { container } = render(<FailedRenewalBanner />);

    expect(container).toBeEmptyDOMElement();
    expect(mockUseQuery).toHaveBeenCalledWith(expect.anything(), {
      skip: true,
    });
  });
});
