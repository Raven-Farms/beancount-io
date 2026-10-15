import { describe, expect, it } from "vitest";
import * as resources from "@/i18n/locales";
import { SUPPORTED_LANGUAGES } from "@/i18n/config";
import enUserProfile from "../en";

// Checking locale files alone misses translations omitted by the runtime aggregator.
describe("user profile runtime translations", () => {
  it.each(SUPPORTED_LANGUAGES)(
    "registers every profile translation in %s",
    (language) => {
      const registered = resources[language];
      for (const key of Object.keys(enUserProfile)) {
        // Plural categories are per language (zh, ja and ko use only
        // `_other`); src/i18n/__tests__/plural.test.ts checks those families.
        if (/_(?:zero|one|two|few|many)$/.test(key)) continue;
        expect(registered[key], `${language}: ${key}`).toBeTruthy();
      }
    },
  );

  it("serves the localized search label instead of the English fallback", () => {
    expect(resources.zh["userProfile.searchLedgers"]).toBe("搜索账簿…");
    expect(resources.ja["userProfile.searchLedgers"]).toBe("帳簿を検索…");
  });
});

describe("profile follower count (w0/021)", () => {
  it("inflects the follower count instead of '1 Followers'", async () => {
    const { createLocalization } = await import("@/i18n/init");
    const { i18n } = createLocalization();
    expect(i18n.t("userProfile.followersCount", { count: 1 })).toBe(
      "1 follower",
    );
    expect(i18n.t("userProfile.followersCount", { count: 401 })).toBe(
      "401 followers",
    );
    i18n.addResourceBundle("ru", "translation", resources.ru);
    await i18n.changeLanguage("ru");
    expect(i18n.t("userProfile.followersCount", { count: 3 })).toBe(
      "3 подписчика",
    );
    expect(i18n.t("userProfile.followersCount", { count: 5 })).toBe(
      "5 подписчиков",
    );
  });

  it("calls starred ledgers ledgers, not repositories", () => {
    expect(enUserProfile["userProfile.noStarredRepos"].message).toBe(
      "No starred ledgers",
    );
  });
});
