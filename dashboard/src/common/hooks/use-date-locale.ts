import { useCallback, useContext } from "react";
import { useTranslation } from "react-i18next";
import type { Locale } from "react-day-picker";
import { useHydrated } from "@tanstack/react-router";
import { LocalizationContext } from "@/i18n/context";
import { defaultDateLocale } from "@/common/lib/format/date-locale";
import { formatRelativeTime } from "@/common/lib/format/format-relative-time";

/**
 * Active app date locale (DayPicker + date-fns). Re-renders when i18n language
 * settles; never follows the browser preference alone.
 * Outside LocalizationProvider (tests), falls back to English.
 */
export function useDateLocale(): Locale {
  const localization = useContext(LocalizationContext);
  const { i18n } = useTranslation();
  // Subscribe to language changes; locale is loaded before changeLanguage settles.
  void i18n.language;
  return localization?.getDateLocale() ?? defaultDateLocale;
}

export function useFormatRelativeTime() {
  const locale = useDateLocale();
  return useCallback(
    (date: Date | number, options?: { addSuffix?: boolean }) =>
      formatRelativeTime(date, locale, options),
    [locale],
  );
}

/**
 * Time labels that render the same on the server and in the hydration pass.
 * Until hydration the server's clock and zone are not the browser's, so both
 * show the exact time in UTC; the age and the browser-zone time then follow
 * in place, keeping the node and the reader's focus (w4/m36).
 */
export function useHydratedTime() {
  const { i18n } = useTranslation();
  const formatRelativeTime = useFormatRelativeTime();
  const hydrated = useHydrated();
  const exactTime = (date: Date, options: Intl.DateTimeFormatOptions) =>
    date.toLocaleString(i18n.language, {
      ...options,
      timeZone: hydrated ? undefined : "UTC",
    });
  return {
    exactTime,
    /** The age once hydrated; until then the exact time in `options`. */
    relativeTime: (date: Date, options: Intl.DateTimeFormatOptions) =>
      hydrated ? formatRelativeTime(date) : exactTime(date, options),
  };
}
