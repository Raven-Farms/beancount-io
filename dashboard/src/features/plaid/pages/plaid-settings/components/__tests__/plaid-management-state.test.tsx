import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { SupportedLanguage } from "@/i18n/config";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import type { PlaidItem } from "../../../../types";
import { PlaidManagementState } from "../plaid-management-state";

vi.unmock("react-i18next");
vi.unmock("@/common/hooks/use-translations");

const { mockToast, mockSyncAll } = vi.hoisted(() => ({
  mockToast: vi.fn(),
  mockSyncAll: vi.fn(),
}));

vi.mock("@/common/hooks/use-toast", () => ({
  useToast: () => ({ toast: mockToast }),
}));

vi.mock("../../../../hooks/use-plaid-accounts", () => ({
  usePlaidItems: () => ({ refetch: vi.fn().mockResolvedValue(undefined) }),
  useUnsyncedTransactions: () => ({
    refetch: vi.fn().mockResolvedValue(undefined),
  }),
  useSyncAllTransactions: () => ({
    syncAllTransactions: mockSyncAll,
    loading: false,
  }),
}));

vi.mock("../../../../components/transaction-review-table", () => ({
  TransactionReviewTable: () => null,
}));

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

async function syncAll(
  language: SupportedLanguage,
  result: {
    transactionsAdded: number;
    institutionsSynced: number;
    skippedCount: number;
  },
) {
  mockSyncAll.mockResolvedValue(result);
  const localization = createLocalization();
  await localization.changeLanguage(language);
  const { getByRole } = render(
    <LocalizationProvider localization={localization}>
      <PlaidManagementState
        items={[{ id: "item-1" } as PlaidItem]}
        ledgerId="alice/personal"
      />
    </LocalizationProvider>,
  );
  fireEvent.click(
    getByRole("button", { name: localization.i18n.t("plaid.management.sync") }),
  );
  await waitFor(() => expect(mockToast).toHaveBeenCalled());
  return mockToast.mock.calls.map(
    ([toast]) => toast as { title: string; description: string },
  );
}

describe("PlaidManagementState sync-all toast", () => {
  it("pluralizes the transaction and bank counts independently", async () => {
    const [one] = await syncAll("en", {
      transactionsAdded: 1,
      institutionsSynced: 1,
      skippedCount: 0,
    });
    expect(one.description).toBe("1 new transaction synced across 1 bank.");

    cleanup();
    mockToast.mockClear();
    const [many] = await syncAll("en", {
      transactionsAdded: 12,
      institutionsSynced: 1,
      skippedCount: 0,
    });
    expect(many.description).toBe("12 new transactions synced across 1 bank.");

    cleanup();
    mockToast.mockClear();
    const [banks] = await syncAll("en", {
      transactionsAdded: 1,
      institutionsSynced: 3,
      skippedCount: 0,
    });
    expect(banks.description).toBe("1 new transaction synced across 3 banks.");
  });

  it("uses each count's own Russian form", async () => {
    const [toast] = await syncAll("ru", {
      transactionsAdded: 5,
      institutionsSynced: 2,
      skippedCount: 0,
    });
    expect(toast.description).toBe(
      "Из 2 банков синхронизировано 5 новых транзакций.",
    );
  });

  it("pluralizes the skipped-banks title", async () => {
    const [, one] = await syncAll("en", {
      transactionsAdded: 0,
      institutionsSynced: 2,
      skippedCount: 1,
    });
    expect(one.title).toBe("1 bank needs reconnecting");

    cleanup();
    mockToast.mockClear();
    const [, many] = await syncAll("en", {
      transactionsAdded: 0,
      institutionsSynced: 2,
      skippedCount: 4,
    });
    expect(many.title).toBe("4 banks need reconnecting");
  });
});
