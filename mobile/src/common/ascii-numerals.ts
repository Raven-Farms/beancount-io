/**
 * Digits typed on other keyboards, as ASCII.
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */

/** The code point of each script's digit zero, ten digits apiece. */
const DIGIT_ZEROS = [
  0x0660, // Arabic-Indic
  0x06f0, // Extended Arabic-Indic (Persian)
  0x07c0, // N'Ko
  0x0966, // Devanagari
  0x09e6, // Bengali
  0x0a66, // Gurmukhi
  0x0ae6, // Gujarati
  0x0b66, // Oriya
  0x0be6, // Tamil
  0x0c66, // Telugu
  0x0ce6, // Kannada
  0x0d66, // Malayalam
  0x0e50, // Thai
  0x0ed0, // Lao
  0x0f20, // Tibetan
  0x1040, // Myanmar
  0x17e0, // Khmer
  0x1810, // Mongolian
  0xff10, // Fullwidth
] as const;

/**
 * Amounts as the ledger keeps them: ASCII. A Persian or Arabic keyboard types
 * `۱۲٫۵۰` or `١٢٫٥٠`, and every such amount was refused as "use digits and one
 * decimal point" (w21/230). Maps each script's digits to 0-9, the Arabic
 * decimal and thousands separators (`٫` `٬`) and the fullwidth period and
 * comma to `.` and `,`.
 */
export function toAsciiNumerals(input: string): string {
  let out = "";
  for (const char of input) {
    const code = char.codePointAt(0) as number;
    const zero =
      code >= 0x80
        ? DIGIT_ZEROS.find((z) => code - z < 10 && code >= z)
        : undefined;
    if (zero !== undefined) out += String(code - zero);
    else if (char === "\u066b" || char === "\uff0e") out += ".";
    else if (char === "\u066c" || char === "\uff0c") out += ",";
    else out += char;
  }
  return out;
}
