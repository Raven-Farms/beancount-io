import fs from "fs";
import path from "path";

// w21/605: the detail's hero icon, calendar, error, tag, link and metadata icons
// were VoiceOver stops of their own (a vector icon renders as Text, so each
// glyph was read). Source check (the screen needs the native runtime).
const screen = fs.readFileSync(
  path.join(__dirname, "..", "transaction-detail-screen.tsx"),
  "utf8",
);
const compact = screen.replace(/\s+/g, "");

describe("the transaction detail's decorative icons", () => {
  it("hide every in-body Ionicons from assistive technology", () => {
    for (const name of [
      "calendar-outline",
      "warning-outline",
      "pricetag-outline",
      "link-outline",
      "document-text-outline",
    ]) {
      expect(
        compact.includes(
          `<Ioniconsname="${name}"accessibilityElementsHiddenimportantForAccessibility="no"`,
        ),
      ).toBe(true);
    }
  });

  it("hides the hero icon's whole subtree", () => {
    expect(
      compact.includes(
        'style={styles.heroIcon}accessible={false}importantForAccessibility="no-hide-descendants"><AccountTypeIconpostings={iconPostings}/>',
      ),
    ).toBe(true);
  });
});
