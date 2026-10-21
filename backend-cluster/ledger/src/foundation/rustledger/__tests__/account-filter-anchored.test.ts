import type { DirectiveJson } from "@rustledger/wasm";
import { filterDirectives } from "@/foundation/rustledger/directive-filter";

/**
 * w21/113: Fava's unanchored search made the account filter `Assets:Cash`
 * also return `Assets:CashApp`, and `Assets:Cas` match at all. REST, GraphQL
 * and MCP journals all filter here.
 */
const txn = (date: string, account: string) =>
  ({
    type: "transaction",
    date,
    flag: "*",
    payee: null,
    narration: account,
    tags: [],
    links: [],
    meta: {},
    postings: [
      { account, units: { number: "1", currency: "USD" }, meta: {} },
      { account: "Equity:Opening", units: { number: "-1", currency: "USD" }, meta: {} },
    ],
  }) as unknown as DirectiveJson;

const ledger = [
  txn("2026-01-01", "Assets:Cash"),
  txn("2026-01-02", "Assets:CashApp"),
  txn("2026-01-03", "Assets:Cash:Wallet"),
  txn("2026-01-04", "Expenses:Food"),
  txn("2026-01-05", "Expenses:TransportFees"),
  txn("2026-01-06", "Assets:Bank:Checking"),
];
const dates = (account: string) =>
  filterDirectives(ledger, { account }).map((directive) => directive.date);

describe("the journal's account filter", () => {
  it("returns an account and its children, not a longer sibling", () => {
    expect(dates("Assets:Cash")).toEqual(["2026-01-01", "2026-01-03"]);
  });

  it("matches no partial name", () => {
    expect(dates("Assets:Cas")).toEqual([]);
    expect(dates("Bank:Check")).toEqual([]);
    expect(dates("Expenses:Transport")).toEqual([]);
  });

  it("still finds a whole component anywhere, case-insensitively", () => {
    expect(dates("Food")).toEqual(["2026-01-04"]);
    expect(dates("assets:cash")).toEqual(["2026-01-01", "2026-01-03"]);
  });

  it("keeps Fava's search for a value written as a pattern", () => {
    expect(dates("^Assets:Cash")).toEqual([
      "2026-01-01",
      "2026-01-02",
      "2026-01-03",
    ]);
    expect(dates("Food|Checking")).toEqual(["2026-01-04", "2026-01-06"]);
  });
});
