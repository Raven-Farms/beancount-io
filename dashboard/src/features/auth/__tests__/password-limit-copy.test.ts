import { describe, expect, it } from "vitest";
import * as locales from "@/i18n/locales";
import { SUPPORTED_LANGUAGES } from "@/i18n/config";
import { numbersIn } from "@/test/locale-scan";

/**
 * Sign-up and reset asked for 6 characters while the server required 8, so a
 * 6- or 7-character password passed the form and was refused with a generic
 * error. Every catalog's copy for a new password must state the bounds
 * `lib/password-rule.ts` enforces. Sign-in keeps its own keys.
 */

const CATALOGS = locales as unknown as Record<string, Record<string, string>>;

describe.each(SUPPORTED_LANGUAGES)("%s new-password copy", (language) => {
  const catalog = CATALOGS[language];

  it("states the 8-character minimum", () => {
    for (const key of [
      "auth.newPasswordMinLength",
      "auth.chooseYourPassword",
    ]) {
      expect(numbersIn(catalog[key]), key).toEqual([8]);
    }
  });

  it("states bcrypt's 72 as the maximum, not the old 128", () => {
    const numbers = numbersIn(catalog["auth.newPasswordMaxLength"]);
    expect(numbers).toContain(72);
    expect(numbers).not.toContain(128);
  });
});
