import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useMutation } from "@apollo/client/react";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { TransactionForm } from "../transaction-form";

vi.mock("@apollo/client/react", () => ({
  useMutation: vi.fn(),
}));

vi.mock("@/common/hooks/use-ledger", () => ({
  useLedger: () => ({ primaryCurrency: "USD" }),
}));

// vi.mock is hoisted above top-level declarations, so the stub lives here.
const { field } = vi.hoisted(() => ({
  field:
    (label: string) =>
    ({
      value,
      onValueChange,
    }: {
      value: string;
      onValueChange: (v: string) => void;
    }) => (
      <input
        aria-label={label}
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
      />
    ),
}));

vi.mock("@/common/components/ledger-comboboxes", () => ({
  AccountCombobox: field("Account"),
  CurrencyCombobox: field("Currency"),
  PayeesCombobox: () => <input aria-label="Payee" />,
  NarrationsCombobox: () => <input aria-label="Narration" />,
}));

const mockUseMutation = vi.mocked(useMutation);

/** Fill posting rows; a blank amount is left for auto-balance. */
function fillPostings(rows: [string, string, string][]) {
  rows.forEach(([account, amount, currency], index) => {
    fireEvent.change(
      screen.getAllByRole("textbox", { name: "Account" })[index]!,
      {
        target: { value: account },
      },
    );
    fireEvent.change(screen.getAllByRole("spinbutton")[index]!, {
      target: { value: amount },
    });
    fireEvent.change(
      screen.getAllByRole("textbox", { name: "Currency" })[index]!,
      { target: { value: currency } },
    );
  });
}

const submit = () =>
  userEvent.click(
    screen.getByRole("button", { name: "Create Transaction Entry" }),
  );

const sentPostings = (mutate: ReturnType<typeof vi.fn>) =>
  mutate.mock.calls[0]?.[0]?.variables?.entries?.[0]?.transaction?.postings;

describe("New Entry refuses unbalanced transactions (w3/499)", () => {
  let addTransaction: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    addTransaction = vi.fn().mockResolvedValue({
      data: { bulkEntries: { success: true } },
    });
    mockUseMutation.mockReturnValue([
      addTransaction,
      { loading: false },
    ] as unknown as ReturnType<typeof useMutation>);
  });

  it("names the residual and sends nothing for 10 / -9 USD", async () => {
    render(<TransactionForm ledgerId="owner/ledger" />);
    fillPostings([
      ["Expenses:Food", "10", "USD"],
      ["Assets:Cash", "-9", "USD"],
    ]);

    await submit();

    expect(
      await screen.findByText(
        "Postings don't balance: 1 USD left over. Adjust an amount, or clear one to balance it automatically.",
      ),
    ).toBeInTheDocument();
    expect(addTransaction).not.toHaveBeenCalled();
  });

  it("submits 10 / -10 USD as typed", async () => {
    render(<TransactionForm ledgerId="owner/ledger" />);
    fillPostings([
      ["Expenses:Food", "10", "USD"],
      ["Assets:Cash", "-10", "USD"],
    ]);

    await submit();

    await waitFor(() => expect(addTransaction).toHaveBeenCalledTimes(1));
    expect(
      sentPostings(addTransaction).map(
        (p: { units: { number: string } }) => p.units.number,
      ),
    ).toEqual(["10", "-10"]);
  });

  it("submits 10 / blank with the inferred -10", async () => {
    render(<TransactionForm ledgerId="owner/ledger" />);
    fillPostings([
      ["Expenses:Food", "10", "USD"],
      ["Assets:Cash", "", "USD"],
    ]);

    await submit();

    await waitFor(() => expect(addTransaction).toHaveBeenCalledTimes(1));
    expect(sentPostings(addTransaction)[1].units.number).toBe("-10");
  });

  it("checks each currency, naming only the one that is off", async () => {
    render(<TransactionForm ledgerId="owner/ledger" />);
    fillPostings([
      ["Expenses:Food", "10", "USD"],
      ["Assets:Cash", "-10", "USD"],
      ["Expenses:Travel", "5", "EUR"],
      ["Assets:Wallet", "-4", "EUR"],
    ]);

    await submit();

    expect(
      await screen.findByText(/^Postings don't balance: 1 EUR left over\./),
    ).toBeInTheDocument();
    expect(addTransaction).not.toHaveBeenCalled();
  });

  it("shows the server's residual when the ledger refuses the entry", async () => {
    addTransaction.mockRejectedValue(
      new CombinedGraphQLErrors({
        errors: [
          {
            message: "entry 0: Transaction does not balance: residual 1 USD",
            extensions: { code: "UNBALANCED", residual: "1 USD", entry: 0 },
          },
        ],
      }),
    );
    render(<TransactionForm ledgerId="owner/ledger" />);
    fillPostings([
      ["Expenses:Food", "10", "USD"],
      ["Assets:Cash", "-10", "USD"],
    ]);

    await submit();

    expect(
      await screen.findByText(/^Postings don't balance: 1 USD left over\./),
    ).toBeInTheDocument();
  });
});
