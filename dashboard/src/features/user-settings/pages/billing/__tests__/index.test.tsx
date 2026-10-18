import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import BillingSettingsPage from "../index";

const mockReactNative = vi.hoisted(() => ({ isReactNative: false }));

vi.mock(
  "@/common/providers/react-native-bridge-provider/react-native-bridge-context",
  () => ({ useReactNativeContext: () => mockReactNative }),
);
vi.mock("@tanstack/react-router", () => ({
  Navigate: ({ to }: { to: string }) => (
    <div data-testid="navigate" data-to={to} />
  ),
}));
vi.mock("@/common/components/seo/page-seo", () => ({ PageSEO: () => null }));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));
vi.mock("../../general/subscription-section", () => ({
  SubscriptionSection: () => <div data-testid="subscription-section" />,
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
});
