import fs from "fs";
import path from "path";
import { recentTransactionsWindow } from "../recent-window";

// w21/471: five pre-entered rent entries filled the "Recent Transactions" card
// and hid the coffee bought yesterday.
describe("Home's Recent Transactions window", () => {
  it("runs up to and including today", () => {
    expect(recentTransactionsWindow("2026-10-21")).toBe(
      "0001-01-01 - 2026-10-21",
    );
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
