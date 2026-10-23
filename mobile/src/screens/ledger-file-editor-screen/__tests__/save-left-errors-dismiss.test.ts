import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

// w21/583: the "Saved, with a new ledger error" alert's dismiss button used the
// `close` key, which is the noun for Beancount's Close directive ("关户" in
// Chinese, "Cierre" in Spanish, "Clôture" in French).
const screen = fs
  .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
  .replace(/\s+/g, "");

describe("the alert after a save that left a new error", () => {
  it("dismisses with Done, not the Close directive's noun", () => {
    const alert = screen.slice(
      screen.indexOf('t("ledgerEditorSaveLeftErrorsTitle")'),
    );
    const buttons = alert.slice(0, alert.indexOf("],"));
    expect(buttons.includes('{text:t("done"),style:"cancel"}')).toBe(true);
    expect(buttons.includes('t("close")')).toBe(false);
    expect(buttons.includes('t("ledgerEditorViewErrors")')).toBe(true);
  });

  it("reads Done in English", () => {
    expect(en.done).toBe("Done");
  });
});
