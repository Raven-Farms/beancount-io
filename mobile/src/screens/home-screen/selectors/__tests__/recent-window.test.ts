import fs from "fs";
import path from "path";
import {
  recentTransactionsUpTo,
  recentTransactionsWindow,
} from "../recent-window";

// w21/471: five pre-entered rent entries filled the "Recent Transactions" card
// and hid the coffee bought yesterday.
describe("Home's Recent Transactions window", () => {
  it("runs through the end of the month, so a later day keeps the cache key", () => {
    expect(recentTransactionsWindow("2026-10-21")).toBe(
      "0001-01-01 - 2026-10-31",
    );
    expect(recentTransactionsWindow("2026-10-22")).toBe(
      recentTransactionsWindow("2026-10-03"),
    );
    expect(recentTransactionsWindow("2026-02-10")).toBe(
      "0001-01-01 - 2026-02-28",
    );
    expect(recentTransactionsWindow("2028-02-10")).toBe(
      "0001-01-01 - 2028-02-29",
    );
  });

  it("keeps the newest rows dated up to today and drops later ones", () => {
    const rows = ["2026-10-30", "2026-10-25", "2026-10-21", "2026-10-20"].map(
      (date) => ({ date }),
    );
    expect(
      recentTransactionsUpTo(rows, "2026-10-22", 5).map((r) => r.date),
    ).toEqual(["2026-10-21", "2026-10-20"]);
    expect(recentTransactionsUpTo(rows, "2026-10-22", 1).length).toBe(1);
  });

  it("is a range the ledger's time filter reads", () => {
    // The ledger's `parseDateRange` needs both ends of a range.
    expect(
      /^\d{4}-\d{2}-\d{2} - \d{4}-\d{2}-\d{2}$/.test(
        recentTransactionsWindow("2026-10-21"),
      ),
    ).toBe(true);
  });

  it("is what the card asks for, following the day past midnight", () => {
    const card = fs
      .readFileSync(
        path.join(
          __dirname,
          "..",
          "..",
          "components",
          "recent-transactions-card.tsx",
        ),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(card.includes("time:recentTransactionsWindow(today),")).toBe(true);
    // `today` is the hook's, so a new day is a new query.
    expect(card.includes("consttoday=useToday();")).toBe(true);
  });
});
