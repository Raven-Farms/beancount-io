import { BadUserInputError } from "@/shared/errors";

/**
 * The tokens a structured entry writes unquoted, checked against Beancount's
 * lexer rules before anything is rendered (w23/033). Written raw, a newline in
 * a tag ended the entry and started directives the caller never sent, and the
 * projected bean-check passed because the smuggled text was valid Beancount.
 *
 * Non-ASCII is accepted wherever Beancount's lexer accepts it, so Unicode
 * account names keep working; whitespace and control characters never are.
 */
const NON_ASCII = "[^\\x00-\\x7F]";
const ACCOUNT = new RegExp(
  `^(?:[A-Z]|${NON_ASCII})(?:[A-Za-z0-9-]|${NON_ASCII})*` +
    `(?::(?:[A-Z0-9]|${NON_ASCII})(?:[A-Za-z0-9-]|${NON_ASCII})*)+$`,
  "u",
);
const NOT_IN_A_TOKEN = /[\s\p{C}]/u;

const TOKEN_RULES = {
  date: /^\d{4}-\d{2}-\d{2}$/,
  flag: /^(?:[*!&#?%PSTCURM]|'[A-Za-z])$/,
  "transaction flag": /^(?:[*!&#?%PSTCURM]|'[A-Za-z]|txn)$/,
  tag: /^[\p{L}\p{N}_/.-]+$/u,
  link: /^[\p{L}\p{N}_/.-]+$/u,
  currency: /^[A-Z](?:[A-Z0-9'._-]{0,22}[A-Z0-9])?$/,
  "metadata key": /^[a-z][A-Za-z0-9_-]*$/,
  account: ACCOUNT,
} as const;

type TokenKind = keyof typeof TOKEN_RULES;

function isToken(kind: TokenKind, value: unknown): boolean {
  return (
    typeof value === "string" &&
    !NOT_IN_A_TOKEN.test(value) &&
    TOKEN_RULES[kind].test(value)
  );
}

type Item = Record<string, unknown>;
const asItem = (value: unknown): Item =>
  value && typeof value === "object" ? (value as Item) : {};
const asList = (value: unknown): unknown[] =>
  Array.isArray(value) ? value : [];

/** Every unquoted token a wire row carries, with the field path a refusal names. */
function rowTokens(row: {
  type: string;
  item: unknown;
}): Array<[string, unknown, TokenKind]> {
  const item = asItem(row.item);
  const tokens: Array<[string, unknown, TokenKind]> = [];
  const add = (field: string, value: unknown, kind: TokenKind) => {
    if (value !== undefined && value !== null)
      tokens.push([field, value, kind]);
  };
  const addAll = (field: string, values: unknown, kind: TokenKind) =>
    asList(values).forEach((value, index) =>
      add(`${field}[${index}]`, value, kind),
    );
  const addAmount = (field: string, amount: unknown) =>
    add(`${field}.currency`, asItem(amount).currency, "currency");

  add("date", item.date, "date");
  add("account", item.account, "account");
  switch (row.type) {
    case "transaction":
      add("flag", item.flag, "transaction flag");
      addAll("tags", item.tags, "tag");
      addAll("links", item.links, "link");
      Object.keys(asItem(item.meta)).forEach((key) =>
        add(`meta.${key}`, key, "metadata key"),
      );
      asList(item.postings).forEach((value, index) => {
        const posting = asItem(value);
        add(`postings[${index}].account`, posting.account, "account");
        add(`postings[${index}].flag`, posting.flag, "flag");
        if (posting.units) addAmount(`postings[${index}].units`, posting.units);
        if (posting.price) addAmount(`postings[${index}].price`, posting.price);
      });
      break;
    case "commodity":
      add("currency", item.currency, "currency");
      break;
    case "price":
      add("currency", item.currency, "currency");
      addAmount("amount", item.amount);
      break;
    case "balance":
      addAmount("amount", item.amount);
      break;
    case "open":
      addAll("currencies", item.currencies, "currency");
      break;
    case "document":
      addAll("tags", item.tags, "tag");
      addAll("links", item.links, "link");
      break;
    case "custom":
      asList(item.values).forEach((value, index) => {
        const custom = asItem(value);
        if (custom.kind === "account")
          add(`values[${index}].value`, custom.value, "account");
        if (custom.kind === "amount")
          add(`values[${index}].currency`, custom.currency, "currency");
      });
      break;
  }
  return tokens;
}

/** Refuse a row whose unquoted tokens would not lex as what they claim to be. */
export function assertEntryTokens(
  rows: Array<{ type: string; item: unknown }>,
): void {
  rows.forEach((row, idx) => {
    for (const [field, value, kind] of rowTokens(row)) {
      if (!isToken(kind, value)) {
        throw new BadUserInputError(
          `entry ${idx}: ${field} ${JSON.stringify(value)} is not a valid ${kind}`,
          field,
        );
      }
    }
  });
}

/**
 * Whether rendered entry text holds exactly one directive: one line that
 * starts at column zero outside a string, the rest indented or blank. A
 * defense behind `assertEntryTokens` for whatever it does not anticipate.
 */
export function isSingleDirective(text: string): boolean {
  let starts = 0;
  let inString = false;
  let lineStart = true;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i]!;
    if (lineStart && !inString && char !== "\n" && !/\s/.test(char))
      starts += 1;
    lineStart = false;
    if (inString) {
      if (char === "\\") i += 1;
      else if (char === '"') inString = false;
      else if (char === "\n") lineStart = true;
      continue;
    }
    if (char === '"') inString = true;
    else if (char === ";") {
      // A comment runs to the end of the line, quotes and all.
      while (i + 1 < text.length && text[i + 1] !== "\n") i += 1;
    } else if (char === "\n") lineStart = true;
  }
  return starts === 1;
}
