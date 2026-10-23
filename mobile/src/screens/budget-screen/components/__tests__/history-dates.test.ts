import fs from "fs";
import path from "path";
import {
  formatLedgerDate,
  formatLedgerDateShort,
} from "../../../../common/date-format";

// w21/366: the history rows, their Delete labels and the Delete alert showed the
// raw ISO date next to a "Starts 1 March 2026" line in the reader's language.
describe("budget history dates", () => {
  it("are written in the reader's language", () => {
    expect(formatLedgerDate("2026-03-01", "de")).toBe("1. März 2026");
    expect(formatLedgerDate("2026-03-01", "en")).toBe("March 1, 2026");
    expect(
      formatLedgerDateShort("2026-03-01", "de").includes("2026-03-01"),
    ).toBe(false);
  });

  it("are what the row, the Delete label and the alert use", () => {
    const src = fs
      .readFileSync(path.join(__dirname, "../budget-history-rows.tsx"), "utf8")
      .replace(/\s+/g, "");
    expect(src.includes("{formatLedgerDateShort(row.date,locale)}")).toBe(true);
    expect(
      src.includes(
        'accessibilityLabel={t("budgetDeleteNamed",{date:formatLedgerDate(row.date,locale),',
      ),
    ).toBe(true);
    expect(src.includes("date:formatLedgerDate(date,locale),")).toBe(true);
    expect(/date:row\.date|\{row\.date\}/.test(src)).toBe(false);
  });
});
