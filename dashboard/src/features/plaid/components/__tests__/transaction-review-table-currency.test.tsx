import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useTranslations } from "@/common/hooks/use-translations";
import { render, screen, within } from "@testing-library/react";
import { TransactionReviewTable } from "../transaction-review-table";
import {
  useUnsyncedTransactions,
  usePlaidAccountsForLedger,
  useSuggestPlaidCategories,
  useSubmitPlaidTransactions,
  useDeletePlaidTransactions,
} from "../../hooks/use-plaid-accounts";

vi.mock("../../hooks/use-plaid-accounts", () => ({
  useUnsyncedTransactions: vi.fn(),
  usePlaidAccountsForLedger: vi.fn(),
  useSuggestPlaidCategories: vi.fn(),
  useSubmitPlaidTransactions: vi.fn(),
  useDeletePlaidTransactions: vi.fn(),
}));

vi.mock("@/common/components/ledger-comboboxes", () => ({
  AccountCombobox: ({
    value,
    onValueChange,
    disabled,
  }: {
    value: string;
    onValueChange: (v: string) => void;
    disabled?: boolean;
  }) => (
    <input
      data-testid="account-combobox"
      value={value}
      onChange={(e) => onValueChange(e.target.value)}
      disabled={disabled}
    />
  ),
  SourceFileCombobox: ({
    value,
    onValueChange,
    disabled,
  }: {
    value: string;
    onValueChange: (v: string) => void;
    disabled?: boolean;
  }) => (
    <input
      data-testid="source-file-combobox"
      value={value}
      onChange={(e) => onValueChange(e.target.value)}
      disabled={disabled}
    />
  ),
}));

const mockUseUnsyncedTransactions = vi.mocked(useUnsyncedTransactions);
const mockUsePlaidAccountsForLedger = vi.mocked(usePlaidAccountsForLedger);
const mockUseSuggestPlaidCategories = vi.mocked(useSuggestPlaidCategories);
const mockUseSubmitPlaidTransactions = vi.mocked(useSubmitPlaidTransactions);
const mockUseDeletePlaidTransactions = vi.mocked(useDeletePlaidTransactions);

const row = (
  id: string,
  plaidAccountId: string,
  amount: string,
  name: string,
) => ({
  id,
  plaidAccountId,
  transactionId: `tx_${id}`,
  date: "2026-01-15T00:00:00.000Z",
  amount,
  merchantName: name,
  name,
  isPending: false,
  accountName: "Account",
  institutionName: "Bank",
  ledgerAccount: "Assets:Bank",
});

const account = (id: string, currency: string) => ({
  id,
  plaidItemId: "item_1",
  accountName: id,
  mask: null,
  institutionName: "Bank",
  currency,
});

describe("TransactionReviewTable amounts and dates (w3/559)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseUnsyncedTransactions.mockReturnValue({
      transactions: [
        // Plaid amounts are positive for money leaving the account.
        row("eur", "pacc_eur", "12", "Euro Cafe"),
        row("usd", "pacc_usd", "-5.5", "Dollar Refund"),
        row("unmapped", "pacc_gone", "3", "Unknown Account"),
      ],
      loading: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useUnsyncedTransactions>);
    mockUsePlaidAccountsForLedger.mockReturnValue({
      accounts: [account("pacc_eur", "EUR"), account("pacc_usd", "USD")],
      loading: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof usePlaidAccountsForLedger>);
    mockUseSuggestPlaidCategories.mockReturnValue({
      suggestCategories: vi.fn().mockResolvedValue([]),
      loading: false,
    } as unknown as ReturnType<typeof useSuggestPlaidCategories>);
    mockUseSubmitPlaidTransactions.mockReturnValue({
      submitTransactions: vi.fn(),
      loading: false,
    } as unknown as ReturnType<typeof useSubmitPlaidTransactions>);
    mockUseDeletePlaidTransactions.mockReturnValue({
      deleteTransactions: vi.fn(),
      loading: false,
    } as unknown as ReturnType<typeof useDeletePlaidTransactions>);
  });

  afterEach(async () => {
    await useTranslations().i18n.changeLanguage("en");
  });

  const rowOf = (name: string) =>
    screen.getAllByText(name)[0]!.closest("tr") as HTMLElement;

  it("shows each row in its account's mapped currency, as booking writes it", () => {
    render(<TransactionReviewTable ledgerId="owner/ledger" />);

    expect(
      within(rowOf("Euro Cafe")).getByText("-12.00 EUR"),
    ).toBeInTheDocument();
    expect(
      within(rowOf("Dollar Refund")).getByText("+5.50 USD"),
    ).toBeInTheDocument();
    // Booking falls back to USD for an account it cannot find; so does review.
    expect(
      within(rowOf("Unknown Account")).getByText("-3.00 USD"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/\$/)).not.toBeInTheDocument();
  });

  it("isolates the amount so RTL layouts keep sign, number and unit in order", () => {
    render(<TransactionReviewTable ledgerId="owner/ledger" />);

    const amount = within(rowOf("Euro Cafe")).getByText("-12.00 EUR");
    expect(amount.tagName).toBe("BDI");
    expect(amount).toHaveAttribute("dir", "ltr");
  });

  it("formats the booked calendar day in the interface language", async () => {
    await useTranslations().i18n.changeLanguage("de");
    render(<TransactionReviewTable ledgerId="owner/ledger" />);

    const expected = new Date("2026-01-15T00:00:00.000Z").toLocaleDateString(
      "de",
      { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" },
    );
    expect(expected).toContain("15");
    expect(within(rowOf("Euro Cafe")).getByText(expected)).toBeInTheDocument();
    expect(screen.queryByText("Jan 15, 2026")).not.toBeInTheDocument();
  });
});
