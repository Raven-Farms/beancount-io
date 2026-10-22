import fs from "fs";
import path from "path";
import { contrastRatio } from "../../../common/theme/color-utils";
import { themes, type ThemeName } from "../../../common/theme/palette";

// w21/382: the drawer's "Couldn't load ledgers" retry put the gray `stateText`
// on the green action fill: 1.01:1 in light, 1.08:1 in dark.
describe("the drawer's retry button", () => {
  for (const name of ["light", "dark"] as ThemeName[]) {
    it(`reads at 4.5:1 in ${name}`, () => {
      const theme = themes[name].colorTheme;
      // `emptyActionText` is `theme.white` on the `theme.primary` fill.
      expect(contrastRatio(theme.white, theme.primary) >= 4.5).toBe(true);
    });
  }

  it("uses the action text style and says Try again, with the error as a caption", () => {
    const src = fs
      .readFileSync(path.join(__dirname, "..", "ledger-drawer.tsx"), "utf8")
      .replace(/\s+/g, "");
    const retry = src.indexOf('testID="drawer-directory-retry"');
    const block = src.slice(retry, retry + 400);
    expect(block.includes("<Textstyle={styles.emptyActionText}>")).toBe(true);
    expect(block.includes('{t("discoveryRetry")}')).toBe(true);
    expect(block.includes("styles.stateText")).toBe(false);
    // The message stays visible, as a caption before the button.
    expect(
      src
        .slice(retry - 300, retry)
        .includes(
          '<Textstyle={styles.stateText}>{t("discoveryLoadError")}</Text>',
        ),
    ).toBe(true);
  });
});
