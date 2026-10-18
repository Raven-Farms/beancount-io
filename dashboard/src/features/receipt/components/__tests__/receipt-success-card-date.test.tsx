import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Locale } from "date-fns";
import { de, enUS, ru, zhCN } from "date-fns/locale";
import { LocalizationContext } from "@/i18n/context";
import type { Localization } from "@/i18n/init";
import { ReceiptSuccessCard } from "../receipt-success-card";

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}));

// The parsed receipt's date reads in the reader's language, not "Feb 13,
// 2026" everywhere (w0/048). English keeps the format it had.
describe("ReceiptSuccessCard date", () => {
  it.each([
    ["de", de, "13. Feb. 2026"],
    ["ru", ru, "13 фев. 2026 г."],
    ["zh", zhCN, "2026-02-13"],
    ["en", enUS, "Feb 13, 2026"],
  ] as [string, Locale, string][])("reads %s", (_code, locale, expected) => {
    render(
      <LocalizationContext.Provider
        value={{ getDateLocale: () => locale } as unknown as Localization}
      >
        <ReceiptSuccessCard
          formData={{
            date: new Date(2026, 1, 13),
            payee: "Café",
            description: "Coffee",
            amount: "4.50",
            currency: "EUR",
            expenseAccount: "Expenses:Food",
            paymentAccount: "Assets:Cash",
            documentAccount: "Assets:Cash",
          }}
          ledgerOwner="o"
          ledgerName="l"
          onReset={() => {}}
        />
      </LocalizationContext.Provider>,
    );
    expect(screen.getByText(expected)).toBeInTheDocument();
  });
});
