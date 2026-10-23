import fs from "fs";
import path from "path";
import { journalLinkFilters } from "../journal-link-filters";
import { resolveAppLink } from "../resolve-app-link";

const ORIGIN = "https://beancount.io";
const journal = (query: string) =>
  resolveAppLink(`${ORIGIN}/ledger/alice/books/journal${query}`)!;
const filters = (query: string) =>
  journalLinkFilters(new URLSearchParams(query));

describe("journal app link filters (w21/344)", () => {
  it("a link without parameters opens unfiltered", () => {
    expect(journal("").filters).toEqual({ statuses: [], range: "all" });
  });

  it("?account= filters to that account", () => {
    const target = journal("?account=Assets%3ABank");
    expect(target.href).toBe("/transactions");
    expect(target.filters).toEqual({
      statuses: [],
      range: "all",
      account: "Assets:Bank",
    });
  });

  it("?time= becomes a custom window for a year, quarter, month, day and range", () => {
    const cases: [string, string, string][] = [
      ["2025", "2025-01-01", "2025-12-31"],
      ["2025-Q2", "2025-04-01", "2025-06-30"],
      ["2025-02", "2025-02-01", "2025-02-28"],
      ["2024-02", "2024-02-01", "2024-02-29"],
      ["2025-03-09", "2025-03-09", "2025-03-09"],
      ["2025-01+-+2025-03", "2025-01-01", "2025-03-31"],
    ];
    for (const [time, startDate, endDate] of cases) {
      expect(filters(`time=${time}`)).toEqual({
        statuses: [],
        range: "custom",
        startDate,
        endDate,
      });
    }
  });

  it("combines account and time", () => {
    expect(
      filters("account=Expenses%3AFood&time=2025-01&filter=%23trip"),
    ).toEqual({
      statuses: [],
      range: "custom",
      startDate: "2025-01-01",
      endDate: "2025-01-31",
      account: "Expenses:Food",
    });
  });

  it("filters nothing for a time it cannot read or an impossible date", () => {
    const none = { statuses: [], range: "all" };
    for (const time of [
      "2025-W10",
      "2025-13",
      "2025-02-30",
      "garbage",
      "2025-03+-+2025-01",
      "",
    ]) {
      expect(filters(`time=${time}`)).toEqual(none);
    }
    expect(filters(`account=${"A".repeat(300)}`)).toEqual(none);
  });

  it("only the journal link carries filters", () => {
    expect(resolveAppLink(`${ORIGIN}/ledger/alice/books/budget`)!.filters).toBe(
      undefined,
    );
  });

  it("opening a link writes its filters under the target ledger", () => {
    const src = fs
      .readFileSync(path.join(__dirname, "../open-app-link.ts"), "utf8")
      .replace(/\s+/g, "");
    expect(
      src.includes(
        "if(target.filters){setTransactionFiltersForLedger(target.ledgerFullName,target.filters);}",
      ),
    ).toBe(true);
    // The canonical (server-cased) target keeps the filters.
    expect(src.includes("return{...target,ledgerFullName:ledgerId,")).toBe(
      true,
    );
  });
});
