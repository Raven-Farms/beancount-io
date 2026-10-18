import type { ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VisibilitySection } from "../index";

const { mutate } = vi.hoisted(() => ({ mutate: vi.fn() }));

vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));
vi.mock("@/common/lib/errors/error-message", () => ({
  useErrorMessage: () => (err: unknown) => String(err),
}));
vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
vi.mock("@apollo/client/react", () => ({
  useMutation: () => [mutate, { loading: false }],
}));
vi.mock("@/common/components/ledger-permission/admin", () => ({
  LedgerAdminPermission: ({ children }: { children: ReactNode }) => (
    <>{children}</>
  ),
}));
vi.mock("@/common/hooks/use-ledger-permission", () => ({
  useLedgerPermission: () => ({ isAdmin: true, canWrite: true, canRead: true }),
}));

const ledger = (isPrivate: boolean) =>
  ({
    id: "ledger-1",
    name: "books",
    fullName: "alice/books",
    private: isPrivate,
  }) as never;
const toggle = () =>
  screen.getByRole("switch", { name: "page.settings.privateLedger" });
const dialog = () =>
  screen.queryByRole("alertdialog", { name: "page.settings.makePublicTitle" });

describe("making a private ledger public asks first (w3/633)", () => {
  beforeEach(() => {
    mutate.mockReset().mockResolvedValue({ data: {} });
  });

  it("opens the confirmation and sends nothing until Make public", async () => {
    const user = userEvent.setup();
    render(<VisibilitySection ledger={ledger(true)} ledgerId="alice/books" />);

    await user.click(toggle());

    expect(dialog()).toBeInTheDocument();
    expect(mutate).not.toHaveBeenCalled();
    // The open dialog hides the page from the accessibility tree.
    expect(
      screen.getByRole("switch", {
        name: "page.settings.privateLedger",
        hidden: true,
      }),
    ).toBeChecked();
    // Cancel, not the exposing action, takes the initial focus.
    expect(screen.getByRole("button", { name: "common.cancel" })).toHaveFocus();

    await user.click(
      screen.getByRole("button", { name: "page.settings.makePublic" }),
    );

    await waitFor(() => expect(mutate).toHaveBeenCalledTimes(1));
    expect(mutate.mock.calls[0]![0].variables).toEqual({
      ledgerId: "alice/books",
      private: false,
    });
  });

  it.each([
    [
      "Cancel",
      () =>
        userEvent.click(screen.getByRole("button", { name: "common.cancel" })),
    ],
    ["Escape", () => userEvent.keyboard("{Escape}")],
  ])(
    "stays private after %s, with focus back on the switch",
    async (_name, leave) => {
      render(
        <VisibilitySection ledger={ledger(true)} ledgerId="alice/books" />,
      );
      await userEvent.click(toggle());

      await leave();

      await waitFor(() => expect(dialog()).not.toBeInTheDocument());
      expect(toggle()).toBeChecked();
      expect(toggle()).toHaveFocus();
      expect(mutate).not.toHaveBeenCalled();
    },
  );

  it("asks on keyboard activation too", async () => {
    const user = userEvent.setup();
    render(<VisibilitySection ledger={ledger(true)} ledgerId="alice/books" />);
    toggle().focus();

    await user.keyboard(" ");

    expect(dialog()).toBeInTheDocument();
    expect(mutate).not.toHaveBeenCalled();
  });

  it("makes a public ledger private in one click", async () => {
    const user = userEvent.setup();
    render(<VisibilitySection ledger={ledger(false)} ledgerId="alice/books" />);

    await user.click(toggle());

    expect(dialog()).not.toBeInTheDocument();
    await waitFor(() => expect(mutate).toHaveBeenCalledTimes(1));
    expect(mutate.mock.calls[0]![0].variables.private).toBe(true);
  });
});
