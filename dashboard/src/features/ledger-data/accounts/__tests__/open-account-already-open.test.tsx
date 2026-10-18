import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { OpenAccountDialog } from "../open-account-dialog";
import { OpenAccountForm } from "@/features/journal/components/new-directive-dialog/open-account-form";

vi.mock("@apollo/client/react", () => ({
  useMutation: () => [vi.fn(), { loading: false }],
  useQuery: (document: { definitions: { name?: { value: string } }[] }) =>
    document.definitions[0]?.name?.value === "GetLedgerAccountDirectives"
      ? {
          data: {
            getLedgerAccountDirectives: [
              {
                account: "Assets:Cash",
                openedAt: "2026-01-01",
                closedAt: null,
              },
              {
                account: "Equity:Opening-Balances",
                openedAt: "2026-01-01",
                closedAt: null,
              },
              {
                account: "Assets:OldBank",
                openedAt: "2025-01-01",
                closedAt: "2025-12-31",
              },
            ],
          },
          loading: false,
        }
      : {
          data: {
            getLedger: {
              options: {
                nameAssets: "Assets",
                nameLiabilities: "Liabilities",
                nameEquity: "Equity",
                nameIncome: "Income",
                nameExpenses: "Expenses",
              },
            },
          },
          loading: false,
        },
}));

vi.mock("@/common/lib/errors/error-message", () => ({
  useErrorMessage: () => () => "error",
}));

vi.mock("@/common/hooks/use-date-locale", async () => {
  const { enUS } = await import("react-day-picker/locale/en-US");
  return { useDateLocale: () => enUS };
});

const surfaces = [
  {
    name: "the Accounts page dialog",
    render: () =>
      render(<OpenAccountDialog open onOpenChange={() => {}} ledgerId="o/l" />),
    field: () => screen.getByLabelText("Account Name"),
    submit: () => screen.getByRole("button", { name: "Open Account" }),
  },
  {
    name: "New Entry's Account tab",
    render: () => render(<OpenAccountForm ledgerId="o/l" />),
    field: () => screen.getByLabelText("Account"),
    submit: () => screen.getByRole("button", { name: "Create Account Entry" }),
  },
];

describe.each(surfaces)("Open Account in $name (w3/557)", (surface) => {
  const type = async (value: string) => {
    fireEvent.change(surface.field(), { target: { value } });
    await waitFor(() => expect(surface.field()).toHaveValue(value));
  };

  it.each([
    ["Assets:Cash", "Assets:Cash is already open (since 2026-01-01)."],
    [
      "Equity:Opening-Balances",
      "Equity:Opening-Balances is already open (since 2026-01-01).",
    ],
    [
      "Assets:OldBank",
      "Assets:OldBank was closed on 2025-12-31; Beancount can't open it again.",
    ],
  ])("refuses %s with its dates", async (account, message) => {
    surface.render();
    await type(account);

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(surface.submit()).toBeDisabled();
  });

  it("accepts a new child of an open account", async () => {
    surface.render();
    await type("Assets:Cash:Wallet");

    await waitFor(() => expect(surface.submit()).toBeEnabled());
    expect(screen.queryByText(/already open/)).not.toBeInTheDocument();
  });

  it("keeps the prefix message for a case-different name", async () => {
    surface.render();
    await type("assets:cash");

    expect(
      await screen.findByText(/^Account must start with one of:/),
    ).toBeInTheDocument();
    expect(surface.submit()).toBeDisabled();
  });
});
