import fs from "fs";
import path from "path";
import { journalRowKeys } from "../../transactions-screen/utils/merge-journal-page";

// w21/524: two identical entries share one entry_hash, so Home's and Reports'
// cards gave both rows one React key.
const card = (...parts: string[]) =>
  fs
    .readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8")
    .replace(/\s+/g, "");

describe("twin entries in the Recent Transactions cards", () => {
  it("get distinct keys", () => {
    const rows = [
      { entry_hash: "h-coffee" },
      { entry_hash: "h-coffee" },
      { entry_hash: "h-rent" },
    ];
    expect([...journalRowKeys(rows).values()]).toEqual([
      "h-coffee",
      "h-coffee#1",
      "h-rent",
    ]);
  });

  it("are keyed through journalRowKeys on Home and in Reports", () => {
    for (const source of [
      card("home-screen", "components", "recent-transactions-card.tsx"),
      card("reports-screen", "components", "account-transactions-card.tsx"),
    ]) {
      expect(source.includes("key={rowKeys.get(entry)??index}")).toBe(true);
      expect(source.includes("key={entry.entry_hash||index}")).toBe(false);
      expect(source.includes("journalRowKeys(entries)")).toBe(true);
    }
  });
});
