import {
  insertDirectives,
  parseDirectiveText,
} from "@/features/ledger/utils/directive-text";
import { BadUserInputError } from "@/shared/errors";

const txn = (date: string, payee: string) =>
  [
    `${date} * "${payee}" "note"`,
    "  Expenses:Food   10.00 USD",
    "  Assets:Cash    -10.00 USD",
  ].join("\n");

describe("parseDirectiveText", () => {
  it("keeps a transaction's postings with it", () => {
    const [directive, ...rest] = parseDirectiveText(txn("2026-03-01", "Cafe"));
    expect(rest).toEqual([]);
    expect(directive).toEqual({
      date: "2026-03-01",
      kind: "Transaction",
      text: txn("2026-03-01", "Cafe"),
    });
  });

  it("splits several directives and classifies each for file routing", () => {
    const directives = parseDirectiveText(
      [
        "2026-01-01 open Assets:Cash USD",
        "",
        txn("2026-02-01", "Shop"),
        "",
        "2026-02-02 price USD 1.00 USD",
        "2026-02-03 balance Assets:Cash 90.00 USD",
      ].join("\n"),
    );
    expect(directives.map((d) => [d.date, d.kind])).toEqual([
      ["2026-01-01", "Open"],
      ["2026-02-01", "Transaction"],
      ["2026-02-02", "Price"],
      ["2026-02-03", "Balance"],
    ]);
  });

  it("carries a comment above a directive along with it", () => {
    const [directive] = parseDirectiveText(
      `; groceries\n${txn("2026-03-01", "Shop")}`,
    );
    expect(directive.text.startsWith("; groceries\n")).toBe(true);
  });

  // w23/041: the stack is positional, but each appended entry moves to its
  // date position, so the statements ended up apart from the entries they
  // annotated. They are applied to those entries instead.
  it("writes a pushed tag onto each enclosed transaction and drops the statements", () => {
    const parsed = parseDirectiveText(
      [
        "pushtag #trip",
        '2026-01-02 * "Cafe" #food ; lunch',
        "  Assets:Cash  -3 USD",
        "  Expenses:Food",
        '2026-01-02 note Assets:Cash "left a tip"',
        "poptag #trip",
        '2026-01-03 * "Home"',
        "  Assets:Cash  -1 USD",
        "  Expenses:Food",
      ].join("\n"),
    );
    expect(parsed.map(({ date, kind }) => ({ date, kind }))).toEqual([
      { date: "2026-01-02", kind: "Transaction" },
      { date: "2026-01-02", kind: "Note" },
      { date: "2026-01-03", kind: "Transaction" },
    ]);
    expect(parsed[0]!.text.split("\n")[0]).toBe(
      '2026-01-02 * "Cafe" #food #trip ; lunch',
    );
    // Beancount tags only transactions from the stack.
    expect(parsed[1]!.text).toBe('2026-01-02 note Assets:Cash "left a tip"');
    expect(parsed[2]!.text).not.toContain("#trip");
  });

  it("writes pushed metadata onto each enclosed directive under its header", () => {
    const parsed = parseDirectiveText(
      [
        'pushmeta trip: "Lisbon"',
        '2026-01-02 * "Cafe"',
        "  Assets:Cash  -3 USD",
        "  Expenses:Food",
        "2026-01-02 open Expenses:Travel",
        '  trip: "kept"',
        "popmeta trip:",
      ].join("\n"),
    );
    expect(parsed[0]!.text.split("\n").slice(0, 2)).toEqual([
      '2026-01-02 * "Cafe"',
      '  trip: "Lisbon"',
    ]);
    // An entry's own value for the key stands.
    expect(parsed[1]!.text).toBe(
      '2026-01-02 open Expenses:Travel\n  trip: "kept"',
    );
  });

  it.each([
    [
      "pushtag #trip\n2026-01-02 open Assets:Cash",
      "line 1: pushed #trip is never popped",
    ],
    [
      'pushmeta trip: "x"\n2026-01-02 open Assets:Cash',
      "line 1: pushed metadata is never popped",
    ],
    [
      "2026-01-02 open Assets:Cash\npoptag #trip",
      "line 2: `poptag #trip` has no matching pushtag",
    ],
    [
      "2026-01-02 open Assets:Cash\npopmeta trip:",
      "line 2: `popmeta trip:` has no matching pushmeta",
    ],
    [
      "pushtag trip\n2026-01-02 open Assets:Cash",
      "line 1: `pushtag` takes one #tag",
    ],
  ])("refuses an unbalanced or malformed stack: %p", (text, message) => {
    expect(() => parseDirectiveText(text)).toThrow(message);
  });

  // w23/018: these reconfigure the whole ledger, and were appended with "No
  // new bean-check errors".
  it.each([
    ['option "operating_currency" "EUR"', "option"],
    ['plugin "beancount.plugins.auto_accounts"', "plugin"],
    ['include "other.bean"', "include"],
  ])("refuses %s, naming the line and the file-edit route", (line, keyword) => {
    const text = `2026-01-02 open Assets:Cash USD\n${line}`;
    expect(() => parseDirectiveText(text)).toThrow(
      new RegExp(`line 2: \`${keyword}\` configures the ledger`),
    );
    try {
      parseDirectiveText(text);
    } catch (error) {
      expect(error).toBeInstanceOf(BadUserInputError);
      expect((error as BadUserInputError).metadata).toMatchObject({
        field: "text",
        hint: expect.stringContaining("updateLedgerFiles"),
      });
    }
  });

  it("refuses content that is not directives, naming the line", () => {
    expect(() =>
      parseDirectiveText("Here are the transactions you asked for:"),
    ).toThrow(BadUserInputError);
    expect(() => parseDirectiveText("+++ b/main.bean")).toThrow(
      /line 1: not a Beancount directive/,
    );
  });

  it("refuses an indented line with no directive above it", () => {
    expect(() => parseDirectiveText("  Expenses:Food 10.00 USD")).toThrow(
      /line 1: indented line has no directive above it/,
    );
  });

  it("refuses text with no directives at all", () => {
    expect(() => parseDirectiveText("\n\n; just a comment\n")).toThrow(
      /no Beancount directives/,
    );
  });
});

describe("insertDirectives", () => {
  const existing = [
    'option "title" "T"',
    "",
    txn("2026-01-05", "Jan"),
    "",
    txn("2026-03-05", "Mar"),
    "",
  ].join("\n");

  it("threads a directive between the two it belongs between", () => {
    const [directive] = parseDirectiveText(txn("2026-02-05", "Feb"));
    const result = insertDirectives(existing, [directive]);

    expect(result.appended).toBe(false);
    const dates = [...result.content.matchAll(/^(\d{4}-\d{2}-\d{2}) \*/gm)].map(
      (match) => match[1],
    );
    expect(dates).toEqual(["2026-01-05", "2026-02-05", "2026-03-05"]);
    // The reported line is where the directive actually starts.
    expect(result.content.split("\n")[result.inserted[0].line - 1]).toBe(
      '2026-02-05 * "Feb" "note"',
    );
  });

  it("keeps a threaded directive's postings with it", () => {
    const [directive] = parseDirectiveText(txn("2026-02-05", "Feb"));
    const { content } = insertDirectives(existing, [directive]);
    const lines = content.split("\n");
    const at = lines.indexOf('2026-02-05 * "Feb" "note"');
    expect(lines[at + 1]).toBe("  Expenses:Food   10.00 USD");
    expect(lines[at + 2]).toBe("  Assets:Cash    -10.00 USD");
  });

  it("does not split an earlier directive from its own postings", () => {
    const [directive] = parseDirectiveText(txn("2026-01-06", "Later same"));
    const { content } = insertDirectives(existing, [directive]);
    const lines = content.split("\n");
    const jan = lines.indexOf('2026-01-05 * "Jan" "note"');
    expect(lines[jan + 1]).toBe("  Expenses:Food   10.00 USD");
    expect(lines[jan + 2]).toBe("  Assets:Cash    -10.00 USD");
  });

  it("puts the newest directive last", () => {
    const [directive] = parseDirectiveText(txn("2026-12-31", "Dec"));
    const { content } = insertDirectives(existing, [directive]);
    expect(content.trimEnd().endsWith("  Assets:Cash    -10.00 USD")).toBe(
      true,
    );
    const dates = [...content.matchAll(/^(\d{4}-\d{2}-\d{2}) \*/gm)].map(
      (match) => match[1],
    );
    expect(dates).toEqual(["2026-01-05", "2026-03-05", "2026-12-31"]);
  });

  it("appends to an unsorted file rather than reordering somebody's ledger", () => {
    const unsorted = [
      txn("2026-05-01", "Late"),
      "",
      txn("2026-01-01", "Early"),
    ].join("\n");
    const [directive] = parseDirectiveText(txn("2026-03-01", "Mid"));
    const result = insertDirectives(unsorted, [directive]);

    expect(result.appended).toBe(true);
    const dates = [...result.content.matchAll(/^(\d{4}-\d{2}-\d{2}) \*/gm)].map(
      (match) => match[1],
    );
    expect(dates).toEqual(["2026-05-01", "2026-01-01", "2026-03-01"]);
  });

  it("writes into an empty file without a leading blank line", () => {
    const [directive] = parseDirectiveText(txn("2026-01-01", "First"));
    const result = insertDirectives("", [directive]);
    expect(result.content).toBe(`${txn("2026-01-01", "First")}\n`);
    expect(result.inserted).toEqual([{ line: 1 }]);
  });

  it("inserts several directives, each in its own place", () => {
    const directives = parseDirectiveText(
      [txn("2026-02-01", "Feb"), "", txn("2026-04-01", "Apr")].join("\n"),
    );
    const { content } = insertDirectives(existing, directives);
    const dates = [...content.matchAll(/^(\d{4}-\d{2}-\d{2}) \*/gm)].map(
      (match) => match[1],
    );
    expect(dates).toEqual([
      "2026-01-05",
      "2026-02-01",
      "2026-03-05",
      "2026-04-01",
    ]);
  });
});
