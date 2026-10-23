import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";
import { translationLocales } from "../../../translations/__tests__/locale-parity";

// w21/265: all four Home "See all" buttons had the same VoiceOver name, so
// Voice Control's "Tap See all" and the rotor could not tell them apart.
describe("the See all buttons name their card", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", "..", "..", ...parts), "utf8")
      .replace(/\s+/g, "");

  it("builds the label from the card's title", () => {
    const card = read("components", "dashboard-card", "index.tsx");
    expect(
      card.includes(
        'accessibilityLabel={title?t("seeAllCard",{title}):t("seeAll")}',
      ),
    ).toBe(true);
    // No button keeps the bare, shared label.
    expect(card.includes('accessibilityLabel={t("seeAll")}')).toBe(false);
  });

  it("names the accounts on the chart card, which has no title of its own", () => {
    const charts = read(
      "screens",
      "home-screen",
      "components",
      "account-charts-card.tsx",
    );
    expect(charts.includes('accessibilityLabel={t("seeAllAccounts")}')).toBe(
      true,
    );
    expect(charts.includes('accessibilityLabel={t("seeAll")}')).toBe(false);
  });

  it("says so in English and every other shipped language", () => {
    expect(en.seeAllCard).toBe("See all {{title}}");
    expect(en.seeAllAccounts).toBe("See all accounts");
    for (const locale of translationLocales()) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const catalog = require(`../../../translations/${locale}`)[locale];
      expect(catalog.seeAllCard.includes("{{title}}")).toBe(true);
      expect(typeof catalog.seeAllAccounts).toBe("string");
    }
  });

  it("tells the four cards' labels apart", () => {
    const label = (title: string) => en.seeAllCard.replace("{{title}}", title);
    const labels = [
      label("Recent Transactions"),
      label("Spending"),
      label("Budget"),
      en.seeAllAccounts,
    ];
    expect(new Set(labels).size).toBe(4);
  });
});
