import fs from "fs";
import path from "path";
import { en } from "../../../../translations/en";
import {
  hasAnyAccountTransaction,
  resolveListAnchor,
  selectAccountTransactions,
} from "../select-account-transactions";
import {
  DirectiveType,
  JournalDirectiveType,
} from "../../../transactions-screen/types";

// w21/266: Recent transactions read "No transactions yet" whenever the income
// statement was loading or had failed, and for any empty range.
function txn(date: string, account: string): JournalDirectiveType {
  return {
    entry_hash: `${date}-${account}`,
    date,
    directive_type: DirectiveType.TRANSACTION,
    flag: "*",
    payee: null,
    narration: null,
    tags: [],
    links: [],
    postings: [{ account, units: { number: "5", currency: "USD" } }],
  } as unknown as JournalDirectiveType;
}

const entries = [
  txn("2026-05-10", "Expenses:Food"),
  txn("2026-03-02", "Income:Salary"),
  txn("2026-01-15", "Expenses:Rent"),
];
const roots = ["Income", "Expenses"];

describe("resolveListAnchor", () => {
  it("keeps the statement's anchor", () => {
    expect(resolveListAnchor("2026-04", false, entries, roots, "2026-10")).toBe(
      "2026-04",
    );
  });

  it("waits while the statement loads", () => {
    expect(resolveListAnchor(null, true, entries, roots, "2026-10")).toBe(null);
  });

  it("falls back to the newest matching entry once the statement failed", () => {
    expect(resolveListAnchor(null, false, entries, roots, "2026-10")).toBe(
      "2026-05",
    );
    const anchor = resolveListAnchor(null, false, entries, roots, "2026-10");
    expect(selectAccountTransactions(entries, roots, "3M", anchor).length).toBe(
      2,
    );
  });

  it("caps the fallback at the current month", () => {
    const future = [txn("2027-02-01", "Expenses:Food")];
    expect(resolveListAnchor(null, false, future, roots, "2026-10")).toBe(
      "2026-10",
    );
  });

  it("has nothing to anchor on without matching entries", () => {
    expect(resolveListAnchor(null, false, [], roots, "2026-10")).toBe(null);
  });
});

describe("hasAnyAccountTransaction", () => {
  it("separates an empty range from an empty ledger", () => {
    expect(hasAnyAccountTransaction(entries, roots)).toBe(true);
    expect(hasAnyAccountTransaction(entries, ["Assets"])).toBe(false);
    expect(hasAnyAccountTransaction([], roots)).toBe(false);
  });
});

describe("the card", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8")
      .replace(/\s+/g, "");

  it("holds the loading tile while the statement loads and picks range copy", () => {
    const card = read("components", "account-transactions-card.tsx");
    expect(
      card.includes("(loading||statementLoading)&&entries.length===0"),
    ).toBe(true);
    expect(card.includes('t("recentTransactionsEmptyRange")')).toBe(true);
    expect(
      read("reports-screen.tsx").includes("statementLoading={isLoading}"),
    ).toBe(true);
  });

  it("says so in English", () => {
    expect(en.recentTransactionsEmptyRange).toBe(
      "No transactions in this range",
    );
  });
});
