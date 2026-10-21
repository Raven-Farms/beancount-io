/**
 * Serialize ordinary Transactions search text into a Fava advanced-filter
 * STRING literal. Bare tokens reject punctuation (e.g. `Mr. Marcel` →
 * Illegal character "."), while quoted strings accept it. The matched value
 * is compiled as a case-insensitive regex, so metacharacters must be escaped
 * before quoting.
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */

/** One tag or link token, in Beancount's tag/link character set. */
const TAG_OR_LINK = /^[#^][A-Za-z0-9_\-./]+$/;

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * @returns A filter expression, or `undefined` when the input is empty/whitespace
 *   so the GraphQL variable can be omitted.
 */
export function toPlainSearchFilter(raw: string): string | undefined {
  const trimmed = raw.trim();
  if (!trimmed) return undefined;

  // A lone `#tag` or `^link` is Fava filter syntax for that tag or link, and
  // only works unquoted: quoted, it matched payee and narration only, so a
  // search for the tags the detail screen shows found nothing (w21/025).
  if (TAG_OR_LINK.test(trimmed)) return trimmed;

  // Lexer forms: `"[^"]*"` and `'[^']*'`, with no escape processing inside.
  // Prefer double quotes; fall back to single quotes when the needle itself
  // contains `"`. When both quote kinds appear, keep double quotes and encode
  // each embedded `"` as the regex escape `\x22`, so the literal still lexes
  // and still matches the quote. `escapeRegExp` escapes typed backslashes
  // first, so a typed `\x22` stays literal text rather than becoming a quote.
  const escaped = escapeRegExp(trimmed);

  if (!escaped.includes('"')) {
    return `"${escaped}"`;
  }
  if (!escaped.includes("'")) {
    return `'${escaped}'`;
  }
  return `"${escaped.replace(/"/g, "\\x22")}"`;
}
