/**
 * The first device language the app supports, else English. Import-free so
 * the unit runner can load it.
 */
export function pickSupportedLocale(
  languageCodes: ReadonlyArray<string | null | undefined>,
  supported: readonly string[],
): string {
  return (
    languageCodes.find(
      (code): code is string => !!code && supported.includes(code),
    ) ?? "en"
  );
}
