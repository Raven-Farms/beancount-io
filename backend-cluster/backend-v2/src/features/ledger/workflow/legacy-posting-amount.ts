import { BadUserInputError } from "@/shared/errors";

/**
 * Beancount's commodity grammar: one uppercase letter, or an uppercase letter
 * then up to 22 of letters, digits and `'._-`, ending in a letter or digit
 * (USD, USDC, MUSD, VBTLX, A1B, TSLA23).
 */
const COMMODITY = String.raw`[A-Z](?:[A-Z0-9'._-]{0,22}[A-Z0-9])?`;
const LEGACY_AMOUNT = new RegExp(`^(-?[\\d,.]+)\\s+(${COMMODITY})$`);

/**
 * Parse a legacy amount string like "11.11 EUR" into a { number, currency }
 * pair. The currency follows Beancount's commodity grammar, not exactly three
 * letters: "11.11 MUSD" or "5.00 VBTLX" was read as a bare number in USD and
 * refused as "not a decimal number", so mobile could add nothing on a ledger
 * in such a currency (w21/190). An amount with no currency is an error, never
 * silently USD.
 */
export function parsePostingAmount(amount: string): {
  number: string;
  currency: string;
} {
  const match = amount.trim().match(LEGACY_AMOUNT);
  if (!match) {
    throw new BadUserInputError(
      `posting amount "${amount}" must be a number followed by a currency, like "11.11 USD"`,
    );
  }
  return { number: match[1].replace(/,/g, ""), currency: match[2] };
}
