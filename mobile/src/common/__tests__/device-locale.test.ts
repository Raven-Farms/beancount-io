import fs from "fs";
import path from "path";
import { pickSupportedLocale } from "../pick-locale";

// w21/126: a fresh install started in English whatever the device said, and a
// Persian device showed English text on an RTL layout.
describe("the first-launch language", () => {
  const supported = ["en", "de", "fa", "zh"];

  it("follows the first supported device language", () => {
    expect(pickSupportedLocale(["de", "en"], supported)).toBe("de");
    expect(pickSupportedLocale(["fa"], supported)).toBe("fa");
    expect(pickSupportedLocale(["xx", null, "zh"], supported)).toBe("zh");
    expect(pickSupportedLocale(["xx"], supported)).toBe("en");
  });

  it("is the app language until the user chooses one", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "vars", "locale.ts"),
      "utf8",
    );
    // A var's default is never written, so a saved choice still wins.
    expect(source.includes('"locale",\n  i18n.locale,')).toBe(true);
  });
});
