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
