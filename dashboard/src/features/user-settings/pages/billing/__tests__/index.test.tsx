import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import BillingSettingsPage from "../index";

const mockReactNative = vi.hoisted(() => ({ isReactNative: false }));

vi.mock(
  "@/common/providers/react-native-bridge-provider/react-native-bridge-context",
  () => ({ useReactNativeContext: () => mockReactNative }),
);
const mockSearch = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
const mockNavigate = vi.hoisted(() => vi.fn());

vi.mock("@tanstack/react-router", () => ({
  Navigate: ({ to }: { to: string }) => (
    <div data-testid="navigate" data-to={to} />
  ),
  useSearch: () => mockSearch.value,
  useNavigate: () => mockNavigate,
}));
vi.mock("@/common/components/seo/page-seo", () => ({ PageSEO: () => null }));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));
vi.mock("../../general/subscription-section", () => ({
  SubscriptionSection: ({
    checkoutReturned,
    returnTo,
    onCheckoutDismiss,
  }: {
    checkoutReturned?: boolean;
    returnTo?: string;
    onCheckoutDismiss?: () => void;
  }) => (
    <div
      data-testid="subscription-section"
      data-checkout={String(checkoutReturned)}
      data-return={returnTo ?? ""}
    >
      <button onClick={onCheckoutDismiss}>dismiss</button>
    </div>
  ),
}));

describe("BillingSettingsPage", () => {
  it("shows the billing heading and the subscription section on the web", () => {
    render(<BillingSettingsPage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "userSettings.billing" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("subscription-section")).toBeInTheDocument();
    expect(screen.queryByTestId("navigate")).not.toBeInTheDocument();
  });

  it("sends the native app's web view to general settings instead of billing", () => {
    mockReactNative.isReactNative = true;
    try {
      render(<BillingSettingsPage />);
      expect(screen.getByTestId("navigate")).toHaveAttribute(
        "data-to",
        "/settings/general",
      );
      expect(
        screen.queryByTestId("subscription-section"),
      ).not.toBeInTheDocument();
    } finally {
      mockReactNative.isReactNative = false;
    }
  });

  it("hands a Checkout return to the subscription section and clears it on dismiss", () => {
    mockSearch.value = { checkout: "success", return: "/ledger/alice/books" };
    try {
      render(<BillingSettingsPage />);
      const section = screen.getByTestId("subscription-section");
      expect(section).toHaveAttribute("data-checkout", "true");
      expect(section).toHaveAttribute("data-return", "/ledger/alice/books");

      screen.getByRole("button", { name: "dismiss" }).click();
      expect(mockNavigate).toHaveBeenCalledWith({
        to: "/settings/billing",
        search: {},
        replace: true,
      });
    } finally {
      mockSearch.value = {};
    }
  });
});
