import { useCallback } from "react";
import { useTranslations } from "@/common/hooks/use-translations";

/**
 * Formats an amount in cents in the **app** language, like
 * `useQuotaNumberFormat` does for counts. Billing is in USD everywhere.
 */
export function useMoneyFormat(): (cents: number, currency?: string) => string {
  const { i18n } = useTranslations();
  const language = i18n.language;
  return useCallback(
    (cents: number, currency = "usd") =>
      new Intl.NumberFormat(language, {
        style: "currency",
        currency: currency.toUpperCase(),
      }).format(cents / 100),
    [language],
  );
}
