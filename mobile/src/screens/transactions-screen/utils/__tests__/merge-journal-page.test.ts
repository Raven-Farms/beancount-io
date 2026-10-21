import fs from "fs";
import path from "path";
import { mergeJournalPage } from "../merge-journal-page";

// Offset paging repeats a row when an entry is added between pages; the lists
// appended it as-is, showing the same transaction twice (w21/035).
const row = (entry_hash: string) => ({ entry_hash });
const PAGE_1 = [
  "farmers",
  "city-bus",
  "whole-foods",
  "sushi",
  "blue-bottle",
].map(row);

describe("mergeJournalPage", () => {
  it("keeps one copy of a row a shifted page repeats, and says so", () => {
    const shifted = [
      "blue-bottle",
      "trader-joes",
      "landlord",
      "acme",
      "visa",
    ].map(row);
    const { data, overlapped } = mergeJournalPage(PAGE_1, shifted);
    expect(data.map((r) => r.entry_hash)).toEqual([
      "farmers",
      "city-bus",
      "whole-foods",
      "sushi",
      "blue-bottle",
      "trader-joes",
      "landlord",
      "acme",
      "visa",
    ]);
    expect(overlapped).toBe(true);
  });

  it("appends an ordinary next page untouched", () => {
    const next = ["trader-joes", "landlord"].map(row);
    expect(mergeJournalPage(PAGE_1, next)).toEqual({
      data: [...PAGE_1, ...next],
      overlapped: false,
    });
  });

  it("keeps rows that carry no hash", () => {
    const { data, overlapped } = mergeJournalPage(
      [{ entry_hash: null }],
      [{ entry_hash: null }],
    );
    expect(data.length).toBe(2);
    expect(overlapped).toBe(false);
  });

  it("reloads from the top in both paged lists when the list moved", () => {
    const read = (...parts: string[]) =>
      fs.readFileSync(path.join(__dirname, "..", "..", "..", ...parts), "utf8");
    const transactions = read("transactions-screen", "transactions-screen.tsx");
    expect(transactions.includes("mergeJournalPage(")).toBe(true);
    expect(
      transactions.includes(
        "if (listMoved) void refetch().catch(() => undefined);",
      ),
    ).toBe(true);
    const merchant = read(
      "merchant-detail-screen",
      "merchant-detail-screen.tsx",
    );
    expect(merchant.includes("mergeJournalPage(")).toBe(true);
    expect(
      merchant.includes(
        "if (listMoved) void refetchJournal().catch(() => undefined);",
      ),
    ).toBe(true);
  });
});
