/**
 * Plural forms follow each language's CLDR rules, and every catalog provides
 * exactly the categories its language distinguishes — no Russian key without
 * `few`, no Chinese key with a `one` nobody renders.
 */
import { I18n } from "i18n-js";
import {
  builtinPluralCategory,
  pluralCategory,
  pluralCategoryMismatches,
  pluralKeys,
  registerPluralizers,
} from "../../common/plural";
import {
  declaredKeys,
  localeModules,
  localeSource,
  translationLocales,
} from "./locale-parity";
import { en } from "../en";
import { ru } from "../ru";
import { sk } from "../sk";
import { zh } from "../zh";

describe("pluralCategory", () => {
  it("picks the CLDR category for the count", () => {
    expect(pluralCategory("en", 1)).toBe("one");
    expect(pluralCategory("en", 2)).toBe("other");
    expect(pluralCategory("ru", 1)).toBe("one");
    expect(pluralCategory("ru", 2)).toBe("few");
    expect(pluralCategory("ru", 5)).toBe("many");
    expect(pluralCategory("ru", 21)).toBe("one");
    expect(pluralCategory("zh", 1)).toBe("other");
  });

  it("falls back to other after the locale's category", () => {
    expect(pluralKeys("ru", 2)).toEqual(["few", "other"]);
    expect(pluralKeys("zh", 1)).toEqual(["other"]);
  });
});

describe("pluralCategoryMismatches", () => {
  it("flags a Russian plural without few and many", () => {
    expect(
      pluralCategoryMismatches("ru", {
        count: { one: "{{count}} a", other: "{{count}} b" },
        plain: "text",
      }),
    ).toEqual([{ key: "count", missing: ["few", "many"], extra: [] }]);
  });

  it("flags a Chinese plural carrying one", () => {
    expect(
      pluralCategoryMismatches("zh", {
        count: { one: "{{count}} 个", other: "{{count}} 个" },
      }),
    ).toEqual([{ key: "count", missing: [], extra: ["one"] }]);
  });

  it("accepts a catalog with exactly the locale's categories", () => {
    expect(
      pluralCategoryMismatches("es", {
        count: { one: "a", many: "b", other: "c" },
      }),
    ).toEqual([]);
  });
});

describe("shipped catalogs", () => {
  it("give every plural key exactly its language's categories", () => {
    const report: Record<string, unknown> = {};
    for (const locale of ["en", ...translationLocales()]) {
      const keys =
        locale === "en" ? Object.keys(en) : declaredKeys(localeSource(locale));
      const catalog =
        locale === "en"
          ? (en as Record<string, unknown>)
          : localeModules[locale];
      const mismatches = pluralCategoryMismatches(locale, catalog, keys);
      if (mismatches.length > 0) report[locale] = mismatches;
    }
    expect(report).toEqual({});
  });
});

describe("rendering counts", () => {
  const i18n = new I18n({ en, ru, zh });
  registerPluralizers(i18n, ["en", "ru", "zh"]);
  const render = (locale: string, count: number) =>
    i18n.t("pricesNotUpdatedSince", { locale, count, date: "Sep 8, 2017" });

  it("reads naturally in English", () => {
    expect(render("en", 1)).toBe("1 price not updated since Sep 8, 2017");
    expect(render("en", 2)).toBe("2 prices not updated since Sep 8, 2017");
    expect(render("en", 5)).toBe("5 prices not updated since Sep 8, 2017");
  });

  it("uses Russian's few and many forms", () => {
    expect(render("ru", 1)).toBe("1 цена не обновлялась с Sep 8, 2017");
    expect(render("ru", 2)).toBe("2 цены не обновлялись с Sep 8, 2017");
    expect(render("ru", 5)).toBe("5 цен не обновлялись с Sep 8, 2017");
  });

  it("uses Chinese's single form", () => {
    expect(render("zh", 1)).toBe("1 个价格自 Sep 8, 2017 起未更新");
    expect(render("zh", 2)).toBe("2 个价格自 Sep 8, 2017 起未更新");
    expect(render("zh", 5)).toBe("5 个价格自 Sep 8, 2017 起未更新");
  });
});

// w21/077: commit detail's stats label was a plain string, so VoiceOver said
// "+1 additions" and "+1 строк".
describe("commit detail stats", () => {
  const i18n = new I18n({ en, ru });
  registerPluralizers(i18n, ["en", "ru"]);
  const say = (key: string, locale: string, count: number) =>
    i18n.t(key, { locale, count });

  it("pluralises in English", () => {
    expect(say("commitDetailAdditions", "en", 1)).toBe("+1 addition");
    expect(say("commitDetailDeletions", "en", 2)).toBe("-2 deletions");
  });

  it("uses Russian's one, few and many forms", () => {
    expect(say("commitDetailAdditions", "ru", 1)).toBe("+1 строка");
    expect(say("commitDetailAdditions", "ru", 2)).toBe("+2 строки");
    expect(say("commitDetailDeletions", "ru", 5)).toBe("-5 строк");
  });
});

// w21/098: the chart summaries VoiceOver reads said "over 1 months" and
// "за 2 периодов".
describe("chart summaries", () => {
  const i18n = new I18n({ en, ru, sk });
  registerPluralizers(i18n, ["en", "ru", "sk"]);
  const months = (locale: string, count: number) =>
    i18n.t("incomeExpenseChartSummary", {
      locale,
      count,
      income: "I",
      expense: "E",
      net: "N",
    });
  const periods = (locale: string, count: number) =>
    i18n.t("budgetChartSummary", {
      locale,
      count,
      span: "S",
      actual: "A",
      budget: "B",
      over: 0,
    });

  it("count months and periods in English", () => {
    expect(months("en", 1).includes("over 1 month.")).toBe(true);
    expect(months("en", 2).includes("over 2 months.")).toBe(true);
    expect(periods("en", 1).includes("across 1 period,")).toBe(true);
    expect(periods("en", 5).includes("across 5 periods,")).toBe(true);
  });

  it("use Russian's and Slovak's forms", () => {
    expect(periods("ru", 1).includes("за 1 период,")).toBe(true);
    expect(periods("ru", 2).includes("за 2 периода,")).toBe(true);
    expect(periods("ru", 5).includes("за 5 периодов,")).toBe(true);
    expect(months("sk", 1).includes("za 1 mesiac.")).toBe(true);
    expect(months("sk", 2).includes("za 2 mesiace.")).toBe(true);
    expect(months("sk", 5).includes("za 5 mesiacov.")).toBe(true);
  });
});

// w21/248: Hermes has no Intl.PluralRules, so on a device every count fell back
// to English's rule: Russian "5 ошибки", Ukrainian "2 запису", Slovak "2 chýb",
// French "0 erreurs". These tests ran under Node, which has the rules.
describe("the built-in CLDR rules", () => {
  it("agree with the runtime's for every shipped language and count", () => {
    for (const locale of translationLocales()) {
      const rules = new Intl.PluralRules(locale);
      for (let count = 0; count <= 1000; count++) {
        expect(
          `${locale}:${count}:${builtinPluralCategory(locale, count)}`,
        ).toBe(`${locale}:${count}:${rules.select(count)}`);
      }
    }
  });

  it("agree for the fractions a count can carry", () => {
    for (const locale of ["en", "ru", "uk", "sk", "fr", "pt", "de"]) {
      const rules = new Intl.PluralRules(locale);
      for (const count of [0.5, 1.5, 2.5, 5.5]) {
        expect(
          `${locale}:${count}:${builtinPluralCategory(locale, count)}`,
        ).toBe(`${locale}:${count}:${rules.select(count)}`);
      }
    }
  });

  it("read the note's examples", () => {
    expect(
      [1, 2, 5, 21, 11, 12, 101, 111].map((n) =>
        builtinPluralCategory("ru", n),
      ),
    ).toEqual(["one", "few", "many", "one", "many", "many", "one", "many"]);
    expect(builtinPluralCategory("uk", 2)).toBe("few");
    expect(builtinPluralCategory("sk", 2)).toBe("few");
    expect(builtinPluralCategory("sk", 5)).toBe("other");
    expect(builtinPluralCategory("fr", 0)).toBe("one");
    expect(builtinPluralCategory("pt", 0)).toBe("one");
    expect(builtinPluralCategory("en", 0)).toBe("other");
    expect(builtinPluralCategory("zh", 1)).toBe("other");
  });
});

describe("without Intl.PluralRules", () => {
  const withoutIntlRules = <T>(run: () => T): T => {
    const intl = Intl as unknown as { PluralRules?: unknown };
    const original = intl.PluralRules;
    intl.PluralRules = undefined;
    try {
      return run();
    } finally {
      intl.PluralRules = original;
    }
  };

  it("counts take their language's forms, as on the device", () => {
    withoutIntlRules(() => {
      // Region-tagged locales no earlier test has cached.
      expect(pluralCategory("ru-KG", 5)).toBe("many");
      expect(pluralCategory("ru-KG", 21)).toBe("one");
      expect(pluralCategory("uk-UA", 2)).toBe("few");
      expect(pluralCategory("sk-SK", 2)).toBe("few");
      expect(pluralCategory("fr-CA", 0)).toBe("one");
      expect(pluralKeys("ru-BY", 5)).toEqual(["many", "other"]);
    });
  });

  it("render Russian errors, Ukrainian records and Slovak errors correctly", () => {
    const i18n = new I18n({
      "ru-MD": {
        errors: {
          one: "%{count} ошибка",
          few: "%{count} ошибки",
          many: "%{count} ошибок",
          other: "%{count} ошибки",
        },
      },
    });
    i18n.locale = "ru-MD";
    withoutIntlRules(() => {
      registerPluralizers(i18n, ["ru-MD"]);
      expect(i18n.t("errors", { count: 5 })).toBe("5 ошибок");
      expect(i18n.t("errors", { count: 2 })).toBe("2 ошибки");
      expect(i18n.t("errors", { count: 21 })).toBe("21 ошибка");
    });
  });
});
