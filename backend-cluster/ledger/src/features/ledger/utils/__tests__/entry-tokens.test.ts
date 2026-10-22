import {
  assertEntryTokens,
  assertSingleEntryText,
  isSingleDirective,
} from "@/features/ledger/utils/entry-tokens";

const txn = (item: Record<string, unknown>) => ({ type: "transaction", item });

describe("assertEntryTokens", () => {
  it.each([
    "Assets:Cash",
    "Assets:Bank:Checking-2",
    "Assets:Café",
    "资产:现金",
    "Liabilities:CreditCard:2026",
  ])("accepts account %p", (account) => {
    expect(() =>
      assertEntryTokens([
        { type: "close", item: { date: "2026-01-01", account } },
      ]),
    ).not.toThrow();
  });

  it.each([
    "Assets",
    "assets:Cash",
    "Assets:Cash Box",
    "Assets:Cash\u00a0Box",
    "Assets:Cash\u2028x",
    "Assets:Ca;sh",
    'Assets:Ca"sh',
  ])("refuses account %p", (account) => {
    expect(() =>
      assertEntryTokens([
        { type: "close", item: { date: "2026-01-01", account } },
      ]),
    ).toThrow(/entry 0: account [\s\S]* is not a valid account/);
  });

  it.each(["*", "!", "txn", "P", "'X"])(
    "accepts transaction flag %p",
    (flag) => {
      expect(() => assertEntryTokens([txn({ flag })])).not.toThrow();
    },
  );

  it.each(["**", "x", "* ", "txn\n"])("refuses transaction flag %p", (flag) => {
    expect(() => assertEntryTokens([txn({ flag })])).toThrow(
      /transaction flag/,
    );
  });

  it.each([
    ["USD", true],
    ["V", true],
    ["BRK.B", true],
    ["usd", false],
    ["US D", false],
    ["USD-", false],
  ])("currency %p is accepted: %p", (currency, ok) => {
    const call = () =>
      assertEntryTokens([
        { type: "commodity", item: { date: "2026-01-01", currency } },
      ]);
    if (ok) expect(call).not.toThrow();
    else expect(call).toThrow(/is not a valid currency/);
  });

  it("refuses a non-string token rather than rendering it", () => {
    expect(() => assertEntryTokens([txn({ tags: [42] })])).toThrow(
      "entry 0: tags[0] 42 is not a valid tag",
    );
  });

  it("names the custom value that is not an account", () => {
    expect(() =>
      assertEntryTokens([
        {
          type: "custom",
          item: {
            date: "2026-01-01",
            type: "budget",
            values: [{ kind: "account", value: "Expenses:Food\n2026-01-01 *" }],
          },
        },
      ]),
    ).toThrow(/entry 0: values\[0\]\.value/);
  });
});

describe("isSingleDirective", () => {
  it.each([
    ['2026-01-01 * "a" "b"\n  Assets:Cash  1 USD\n  Equity:X\n\n', true],
    // A string may span lines; its continuation is not a directive.
    ['2026-01-01 * "two\n2026-01-02 lines"\n  Assets:Cash  1 USD\n', true],
    ['2026-01-01 * "esc \\" quote"\n  a: "x ; y"\n', true],
    ['2026-01-01 * "a"\n2026-01-01 note Assets:Cash "x"\n', false],
    ['2026-01-01 * "a"\noption "title" "x"\n', false],
    ["\n\n", false],
  ])("%p is one directive: %p", (text, single) => {
    expect(isSingleDirective(text)).toBe(single);
  });
});

describe("assertSingleEntryText", () => {
  it.each([
    '2026-01-01 * "a"\n  Assets:Cash  1 USD\n  Equity:X',
    '; why\n2026-01-01 * "a"\n  Assets:Cash  1 USD\n  Equity:X\n; after\n',
    '2026-01-01 * "two\nlines"\n  Assets:Cash  1 USD\n  Equity:X',
    "2026-01-01 open Assets:Cash USD",
  ])("accepts %p", (text) => {
    expect(() => assertSingleEntryText(text, "newContent")).not.toThrow();
  });

  it.each([
    ['plugin "beancount.plugins.auto"', "`plugin` configures the ledger"],
    ["2026-01-01 open A:B\n2026-01-02 open A:C", "newContent holds 2 entries"],
    ["  indented only", "newContent holds no entry"],
    ['  2026-01-01 * "a"', "newContent holds no entry"],
    ["Assets:Cash 1 USD", "newContent must be one dated directive"],
  ])("refuses %p", (text, message) => {
    expect(() => assertSingleEntryText(text, "newContent")).toThrow(message);
  });
});
