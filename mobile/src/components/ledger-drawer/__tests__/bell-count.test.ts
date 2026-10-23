import fs from "fs";
import path from "path";
import { I18n } from "i18n-js";
import { registerPluralizers } from "../../../common/plural";
import { en } from "../../../translations/en";
import { ru } from "../../../translations/ru";

// w21/109: VoiceOver read the bell as "Notifications, button" while sighted
// users saw a red error count.
describe("the Notifications bell", () => {
  it("speaks its error count as its value", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "ledger-drawer-header.tsx"),
      "utf8",
    );
    expect(
      source.includes('? { text: t("ledgerEditorErrorCount", { count }) }'),
    ).toBe(true);
  });

  it("reads 1 error, pluralised", () => {
    const i18n = new I18n({ en, ru });
    registerPluralizers(i18n, ["en", "ru"]);
    expect(i18n.t("ledgerEditorErrorCount", { locale: "en", count: 1 })).toBe(
      "1 error",
    );
    expect(i18n.t("ledgerEditorErrorCount", { locale: "ru", count: 1 })).toBe(
      "1 ошибка",
    );
  });
});

// w21/625: at AX2 the count's text outgrew the fixed 16pt pill and was clipped.
describe("the bell's error badge at large text sizes", () => {
  const source = fs
    .readFileSync(
      path.join(__dirname, "..", "ledger-drawer-header.tsx"),
      "utf8",
    )
    .replace(/\s+/g, "");

  it("caps how far its count scales", () => {
    expect(source.includes("constBADGE_MAX_FONT_SIZE_MULTIPLIER=1.3;")).toBe(
      true,
    );
    expect(
      source.includes("maxFontSizeMultiplier={BADGE_MAX_FONT_SIZE_MULTIPLIER}"),
    ).toBe(true);
  });

  it("lets the pill grow with its text instead of clipping it", () => {
    expect(source.includes("minHeight:16,borderRadius:9,")).toBe(true);
    expect(source.includes("height:16,")).toBe(false);
  });
});
