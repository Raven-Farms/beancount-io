import type { ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { VisibilitySection } from "../index";

vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));

vi.mock("@/common/lib/errors/error-message", () => ({
  useErrorMessage: () => (err: unknown) => String(err),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock("@apollo/client/react", () => ({
  useMutation: () => [vi.fn(), { loading: false }],
}));

vi.mock("@/common/components/ledger-permission/admin", () => ({
  LedgerAdminPermission: ({ children }: { children: ReactNode }) => (
    <>{children}</>
  ),
}));

vi.mock("@/common/hooks/use-ledger-permission", () => ({
  useLedgerPermission: () => ({ isAdmin: true, canWrite: true, canRead: true }),
}));

const publicLedger = {
  id: "ledger-1",
  name: "example",
  fullName: "open_ledger/example",
  private: false,
} as const;

describe("VisibilitySection sharing copy buttons", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { origin: "https://beancount.io" },
    });
  });

  it("names shareable URL and embed copy buttons through copied state", async () => {
    const user = userEvent.setup();
    render(
      <VisibilitySection ledger={publicLedger as never} ledgerId="ledger-1" />,
    );

    const urlButton = screen.getByRole("button", {
      name: "page.settings.copyShareableUrl",
    });
    const embedButton = screen.getByRole("button", {
      name: "page.settings.copyEmbedCode",
    });

    await user.click(urlButton);
    await waitFor(() => {
      expect(urlButton.querySelector(".lucide-check")).toBeTruthy();
    });
    expect(
      screen.getByRole("button", { name: "page.settings.copyShareableUrl" }),
    ).toBeInTheDocument();

    await user.click(embedButton);
    await waitFor(() => {
      expect(embedButton.querySelector(".lucide-check")).toBeTruthy();
    });
    expect(
      screen.getByRole("button", { name: "page.settings.copyEmbedCode" }),
    ).toBeInTheDocument();
  });
});

describe("VisibilitySection switch name (w0/013)", () => {
  it("names the switch for what on means, in both states, with its description", () => {
    const { unmount } = render(
      <VisibilitySection ledger={publicLedger as never} ledgerId="ledger-1" />,
    );
    const publicSwitch = screen.getByRole("switch", {
      name: "page.settings.privateLedger",
    });
    expect(publicSwitch).not.toBeChecked();
    expect(publicSwitch).toHaveAccessibleDescription(
      "page.settings.publicLedgerDescription",
    );
    unmount();

    render(
      <VisibilitySection
        ledger={{ ...publicLedger, private: true } as never}
        ledgerId="ledger-1"
      />,
    );
    const privateSwitch = screen.getByRole("switch", {
      name: "page.settings.privateLedger",
    });
    expect(privateSwitch).toBeChecked();
    expect(privateSwitch).toHaveAccessibleDescription(
      "page.settings.privateLedgerDescription",
    );
  });
});
