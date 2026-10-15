/**
 * Format a number respecting the beancount render_commas option.
 *
 * @param value       - The numeric value to format
 * @param renderCommas - When true, adds thousands separators (e.g. 1,234,567.89).
 *                       When false, omits them (e.g. 1234567.89).
 * @param locale      - Explicit formatting locale. Required for separators:
 *                      without it `toLocaleString` uses the runtime default, so
 *                      the server renders "80,149.807" and a French browser
 *                      hydrates "80 149,807", which React resolves by throwing
 *                      away and regenerating the server-rendered report tree.
 * @returns Formatted number string
 */
export const formatNumber = (
  value: number,
  renderCommas: boolean,
  locale: string,
  currency?: string,
): string => {
  // An ISO 4217 currency is written at its minor-unit precision in both
  // render_commas modes — `4,559.80` and `109,529.34 USD`, never `4,559.8` or
  // `109,529.339` — so the option controls grouping only (w0/010).
  const digits = currency ? currencyMinorDigits(currency) : undefined;
  if (digits !== undefined) {
    return value.toLocaleString(locale, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
      useGrouping: renderCommas,
    });
  }
  if (renderCommas) {
    return value.toLocaleString(locale);
  }
  if (Number.isInteger(value)) {
    return String(value);
  }
  // Preserve up to 2 decimal places, strip trailing zeros
  return value.toFixed(2).replace(/\.?0+$/, "");
};

let isoCurrencies: Set<string> | null = null;
const minorDigitsCache = new Map<string, number | undefined>();

/**
 * The fraction digits an ISO 4217 currency is written with (USD 2, JPY 0,
 * KWD 3), or `undefined` for a commodity that is not one — tickers (`VHT`,
 * `GLD`), crypto (`BTC`) and ledger-defined units (`MUSD`, `VACHR`) keep the
 * source-driven formatting, so their recorded precision is never cut.
 */
export function currencyMinorDigits(currency: string): number | undefined {
  if (minorDigitsCache.has(currency)) return minorDigitsCache.get(currency);
  let digits: number | undefined;
  try {
    isoCurrencies ??= new Set(Intl.supportedValuesOf("currency"));
    if (isoCurrencies.has(currency)) {
      digits = new Intl.NumberFormat("en", {
        style: "currency",
        currency,
      }).resolvedOptions().maximumFractionDigits;
    }
  } catch {
    digits = undefined;
  }
  minorDigitsCache.set(currency, digits);
  return digits;
}

/**
 * How many fraction digits a source decimal carries — `"4.00995"` → 5.
 *
 * Read from the string the ledger sent, never from the parsed double: asking a
 * double for "all" its digits prints binary artifacts (0.1 + 0.2 becomes
 * 0.30000000000000004), while the source string says exactly how much
 * precision is real.
 */
export const fractionDigitsOf = (
  source: string | number | null | undefined,
): number => {
  if (source === null || source === undefined) return 0;
  const text = typeof source === "number" ? String(source) : source.trim();
  const separator = text.indexOf(".");
  if (separator === -1) return 0;
  const fraction = text.slice(separator + 1).replace(/[^0-9].*$/, "");
  return Math.min(fraction.length, 20);
};

/**
 * Format a quantity for a detailed tooltip, keeping the digits the ledger sent.
 *
 * `formatNumber` is built for cash: it caps at the locale default of three
 * fraction digits, or `toFixed(2)` without separators. That rounds real
 * commodity units — 4.00995 ETH read as 4.01 beside a journal showing the full
 * quantity. Here the digit budget comes from the source decimal instead, so
 * nothing is invented and nothing is dropped. Grouping, locale separators and
 * the no-trailing-zeros shape are unchanged, and a value whose source has two
 * decimals still formats exactly as before.
 */
export const formatQuantity = (
  value: number,
  fractionDigits: number,
  renderCommas: boolean,
  locale: string,
): string => {
  const digits = Math.min(Math.max(Math.trunc(fractionDigits) || 0, 0), 20);
  if (renderCommas) {
    return value.toLocaleString(locale, { maximumFractionDigits: digits });
  }
  if (Number.isInteger(value)) {
    return String(value);
  }
  return value.toFixed(digits).replace(/\.?0+$/, "");
};
