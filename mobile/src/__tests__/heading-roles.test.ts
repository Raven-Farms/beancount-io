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

  it("reads a date header's day total as part of it", () => {
    expect(
      read("screens/transactions-screen/date-section-header.tsx").includes(
        't("dateSectionHeaderTotal", { date: displayDate, total })',
      ),
    ).toBe(true);
  });
});
