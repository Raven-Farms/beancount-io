import fs from "fs";
import path from "path";

// The New Transaction row draws an add-circle icon and then the addPosting
// label. Every locale's label still began with "+ ", so the row read
// "⊕ + Add posting" and VoiceOver announced "plus Add posting" (w0/035).
const dir = path.join(__dirname, "..", "translations");
const locales = fs
  .readdirSync(dir)
  .filter((file) => /^[a-z]{2}\.ts$/.test(file))
  .map((file) => file.slice(0, 2));

describe("Add posting row", () => {
  it("covers every locale", () => {
    expect(locales.length).toBe(13);
  });

  for (const locale of locales) {
    it(`labels the row without a second plus in ${locale}`, () => {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const messages = require(path.join(dir, locale))[locale] as Record<
        string,
        string
      >;
      expect(typeof messages.addPosting).toBe("string");
      expect(/^\s*[+＋]/.test(messages.addPosting)).toBe(false);
    });
  }

  it("draws the plus as the row's icon", () => {
    const screen = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "screens/multi-postings-transaction/multi-postings-transaction-screen.tsx",
      ),
      "utf8",
    );
    const row = screen.slice(
      screen.indexOf("style={styles.addPostingRow}"),
      screen.indexOf('{t("addPosting")}</Text>'),
    );
    expect(row.includes('name="add-circle-outline"')).toBe(true);
    expect(row.includes('accessibilityLabel={t("addPosting")}')).toBe(true);
  });
});
