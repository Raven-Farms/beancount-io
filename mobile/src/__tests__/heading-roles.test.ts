import fs from "fs";
import path from "path";

/**
 * w21/143: date sections, Merchants and account-picker sections and card
 * titles were not headings, so VoiceOver's Headings rotor could not step
 * through a long journal.
 */
const read = (relative: string) =>
  fs.readFileSync(path.join(__dirname, "..", relative), "utf8");

describe("section and card titles are headings", () => {
  for (const file of [
    "screens/transactions-screen/date-section-header.tsx",
    "screens/merchants-screen/merchants-screen.tsx",
    "screens/account-picker-screen/account-picker-screen.tsx",
    "components/dashboard-card/index.tsx",
  ]) {
    it(`marks the title in ${file}`, () => {
      expect(read(file).includes('accessibilityRole="header"')).toBe(true);
    });
  }

  // w21/320: w21/143 missed these section titles.
  it("marks the remaining section titles", () => {
    const compactRead = (relative: string) =>
      read(relative).replace(/\s+/gu, "");
    const titled = (relative: string, key: string) => {
      const source = compactRead(relative);
      const at = source.indexOf(`t("${key}")`);
      expect(at > -1).toBe(true);
      // The role sits on the Text that opens just before the title.
      const open = source.lastIndexOf("<Text", at);
      expect(
        source.slice(open, at).includes('accessibilityRole="header"'),
      ).toBe(true);
    };
    titled(
      "screens/account-detail-screen/account-detail-screen.tsx",
      "transactions",
    );
    titled(
      "screens/transaction-detail-screen/transaction-detail-screen.tsx",
      "moneyFlow",
    );
    titled(
      "screens/transaction-detail-screen/transaction-detail-screen.tsx",
      "details",
    );
    titled(
      "screens/transactions-screen/entry-context/index.tsx",
      "journalSource",
    );
    for (const key of ["filterStatus", "filterDateRange", "filterAccount"])
      titled(
        "screens/transaction-filters-screen/transaction-filters-screen.tsx",
        key,
      );
    // Settings' section headers (Support, About, …) share one component.
    expect(
      compactRead("screens/setting/list-item.tsx").includes(
        '<Textstyle={styles.title}accessibilityRole="header">{title}</Text>',
      ),
    ).toBe(true);
  });

  it("reads a date header's day total as part of it", () => {
    expect(
      read("screens/transactions-screen/date-section-header.tsx").includes(
        't("dateSectionHeaderTotal", { date: displayDate, total })',
      ),
    ).toBe(true);
  });
});
