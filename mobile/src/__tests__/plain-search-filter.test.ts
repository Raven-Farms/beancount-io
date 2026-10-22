import { toPlainSearchFilter } from "../screens/transactions-screen/utils/plain-search-filter";

describe("toPlainSearchFilter", () => {
  it("returns undefined for empty or whitespace input", () => {
    expect(toPlainSearchFilter("")).toBe(undefined);
    expect(toPlainSearchFilter("   ")).toBe(undefined);
  });

  it("quotes and escapes punctuation so merchant periods stay literal", () => {
    expect(toPlainSearchFilter("Mr. Marcel")).toBe('"Mr\\. Marcel"');
  });

  it("preserves apostrophes inside double quotes", () => {
    expect(toPlainSearchFilter("O'Brien")).toBe(`"O['\u2018\u2019]Brien"`);
  });

  it("double-quotes a needle that contains double quotes", () => {
    // Always double-quoted, the double quote written as a regex escape.
    expect(toPlainSearchFilter('say "hi"')).toBe(
      '"say [\\x22\u201c\u201d]hi[\\x22\u201c\u201d]"',
    );
  });

  describe("when both quote kinds appear", () => {
    // Mirrors the filter service: its STRING lexer takes `"[^"]*"` or
    // `'[^']*'` verbatim (no escape processing), and the body is compiled as a
    // case-insensitive JavaScript regex.
    const compile = (raw: string): RegExp => {
      const filter = toPlainSearchFilter(raw);
      if (filter === undefined) throw new Error("expected a filter");
      const lexed = /^(?:"[^"]*"|'[^']*')$/.exec(filter);
      if (!lexed) throw new Error(`not one STRING token: ${filter}`);
      return new RegExp(filter.slice(1, -1), "i");
    };

    it("matches text containing both quote kinds, not the quote-stripped text", () => {
      const regex = compile(`E.B.'s "Beer"`);
      expect(regex.test(`E.B.'s "Beer" and Wine`)).toBe(true);
      expect(regex.test(`E.B.'s Beer and Wine`)).toBe(false);
    });

    it("keeps typed backslashes literal beside quotes", () => {
      const regex = compile(`a\\"b'`);
      expect(regex.test(`a\\"b'`)).toBe(true);
      expect(regex.test(`a"b'`)).toBe(false);
    });

    it("does not turn a typed \\x22 into a quote", () => {
      const regex = compile(`it's \\x22 "q"`);
      expect(regex.test(`it's \\x22 "q"`)).toBe(true);
      expect(regex.test(`it's " "q"`)).toBe(false);
    });
  });

  it("trims surrounding whitespace before encoding", () => {
    expect(toPlainSearchFilter("  Marcel  ")).toBe('"Marcel"');
  });

  // Merchant detail routes its journal needle through here too, so the payees
  // that used to break it are pinned as serializer cases.
  it("escapes a decimal point in a merchant name", () => {
    expect(toPlainSearchFilter("Ethereum 2.0")).toBe('"Ethereum 2\\.0"');
  });

  it("keeps an apostrophe payee inside double quotes", () => {
    expect(toPlainSearchFilter("Lowe's")).toBe(`"Lowe['\u2018\u2019]s"`);
  });

  it("escapes a trailing period in a company suffix", () => {
    expect(toPlainSearchFilter("MiniMax Group Inc.")).toBe(
      '"MiniMax Group Inc\\."',
    );
  });

  it("double-quotes a payee with an embedded double quote", () => {
    expect(toPlainSearchFilter('The "Best" Cafe')).toBe(
      '"The [\\x22\u201c\u201d]Best[\\x22\u201c\u201d] Cafe"',
    );
  });
});

// A lone tag or link is Fava filter syntax and must reach it unquoted: the
// quoted form matched payee and narration only (w21/025). It is also how a check
// or order number reads in a narration ("Check #1042"), so it goes with the text
// as an alternative (`,` is Fava's OR) (w21/400).
describe("toPlainSearchFilter tags and links", () => {
  it("sends a single tag or link token as the tag or the text", () => {
    expect(toPlainSearchFilter(" #work ")).toBe('#work,"#work"');
    expect(toPlainSearchFilter("^qa-receipt-001")).toBe(
      '^qa-receipt-001,"\\^qa-receipt-001"',
    );
    expect(toPlainSearchFilter("#trip/2026.q3")).toBe(
      '#trip/2026.q3,"#trip/2026\\.q3"',
    );
  });

  it("finds a check number in a narration as well as a real tag", () => {
    expect(toPlainSearchFilter("#1042")).toBe('#1042,"#1042"');
    expect(toPlainSearchFilter("#112-3456789-1234567")).toBe(
      '#112-3456789-1234567,"#112-3456789-1234567"',
    );
  });

  it("keeps quoting anything that is not exactly one token", () => {
    expect(toPlainSearchFilter("#a b")).toBe('"#a b"');
    expect(toPlainSearchFilter("#")).toBe('"#"');
    expect(toPlainSearchFilter("coffee #work")).toBe('"coffee #work"');
    expect(toPlainSearchFilter("#café")).toBe('"#café"');
  });
});

// w21/401: iOS Smart Punctuation turns a typed apostrophe into U+2019, which
// matched nothing against the straight quote in the ledger, and the reverse.
describe("toPlainSearchFilter and typographic quotes", () => {
  const compile = (raw: string): RegExp => {
    const filter = toPlainSearchFilter(raw);
    if (filter === undefined) throw new Error("expected a filter");
    const lexed = /^"[^"]*"$/.exec(filter);
    if (!lexed) throw new Error(`not one STRING token: ${filter}`);
    return new RegExp(filter.slice(1, -1), "i");
  };

  it("finds a straight apostrophe from the curly one iOS types, and the reverse", () => {
    expect(compile("Trader Joe\u2019s").test("TRADER JOE'S #123")).toBe(true);
    expect(compile("Trader Joe's").test("Trader Joe\u2019s")).toBe(true);
    expect(compile("Trader Joe\u2018s").test("Trader Joe's")).toBe(true);
    expect(compile("Trader Joe's").test("Trader Joes")).toBe(false);
  });

  it("finds straight double quotes from curly ones and the reverse", () => {
    expect(
      compile("E.B.'s \u201cBeer\u201d").test(`E.B.'s "Beer" and Wine`),
    ).toBe(true);
    expect(compile('The "Best" Cafe').test("The \u201cBest\u201d Cafe")).toBe(
      true,
    );
    expect(compile('The "Best" Cafe').test("The Best Cafe")).toBe(false);
  });

  it("stays one lexable literal whatever quotes it holds", () => {
    for (const text of [`a'b`, `a"b`, `a'b"c`, `\u2019\u201c`]) {
      expect(/^"[^"]*"$/.test(toPlainSearchFilter(text) ?? "")).toBe(true);
    }
  });
});
