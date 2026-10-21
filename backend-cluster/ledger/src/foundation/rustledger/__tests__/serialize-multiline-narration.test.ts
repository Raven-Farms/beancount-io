import { entryInputToText } from "@/foundation/rustledger/entry-build";
import type { LedgerEntryInput } from "@/foundation/ledger-api-types/ledger-entry-input";

/**
 * w21/191: the serializer's align and per-line rstrip ran on every physical
 * line, including lines inside a multi-line string, so a narration line ending
 * in "2 x Milk 3.50 EUR" gained ~50 spaces and trailing spaces and \r were
 * dropped. Checked with the real parser: the narration reads back unchanged.
 */
const entry = (narration: string): LedgerEntryInput => ({
  type: "transaction",
  entry: {
    date: "2026-08-30",
    flag: "*",
    payee: undefined,
    narration,
    tags: [],
    links: [],
    postings: [
      { account: "Expenses:Food", units: { number: "3.50", currency: "EUR" } },
      { account: "Assets:Cash", units: { number: "-3.50", currency: "EUR" } },
    ],
  },
});

/** The narration back out of the serialized text: everything between the quotes. */
function narrationOf(text: string): string {
  const open = text.indexOf('"');
  const close = text.indexOf('"\n', open + 1);
  const end = close === -1 ? text.indexOf('" ', open + 1) : close;
  return text
    .slice(open + 1, end)
    .replace(/\\"/g, '"')
    .replace(/\\\\/g, "\\");
}

describe("multi-line narration survives serialization", () => {
  it.each([
    ["an amount-like last line", "Groceries\n2 x Milk 3.50 EUR"],
    ["trailing spaces", "line one   \nline two"],
    ["a carriage return", "x\r\ny"],
    ["quotes, tabs and RTL text", 'say "hi"\t\nمرحبا'],
  ])("%s", (_name, narration) => {
    expect(narrationOf(entryInputToText(entry(narration)))).toBe(narration);
  });

  it("still aligns the postings", () => {
    const text = entryInputToText(entry("Groceries\n2 x Milk 3.50 EUR"));
    expect(text).toContain("  Expenses:Food");
    const posting = text
      .split("\n")
      .find((line) => line.includes("Expenses:Food"));
    // The currency sits in column 61 as before.
    expect(posting?.indexOf("EUR")).toBe(60);
  });
});
