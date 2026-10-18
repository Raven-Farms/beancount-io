import { describe, expect, it } from "vitest";
import { syncLocaleEntries, type TranslationEntry } from "../lib/sync-locale";

const entry = (message: string, description = "d"): TranslationEntry => ({
  message,
  description,
});

// English writes a count as `_one` / `_other`; other languages use their own
// CLDR categories, and the sync must keep them (w0/m3).
const english = {
  "files.count_one": entry("{{count}} file", "count of files"),
  "files.count_other": entry("{{count}} files", "count of files"),
  "files.title": entry("Files"),
};

describe("syncLocaleEntries", () => {
  it("keeps Russian few and many forms English does not have", () => {
    const russian = {
      "files.count_one": entry("{{count}} файл"),
      "files.count_few": entry("{{count}} файла"),
      "files.count_many": entry("{{count}} файлов"),
      "files.count_other": entry("{{count}} файла"),
      "files.title": entry("Файлы"),
    };
    const result = syncLocaleEntries(english, russian, "ru");
    expect(result.added).toEqual([]);
    expect(result.removed).toEqual([]);
    expect(result.entries).toEqual(russian);
  });

  it.each(["uk", "sk"])("keeps %s plural forms", (locale) => {
    const catalog = {
      "files.count_one": entry("1"),
      "files.count_few": entry("2"),
      "files.count_many": entry("5"),
      "files.count_other": entry("x"),
      "files.title": entry("t"),
    };
    expect(syncLocaleEntries(english, catalog, locale).removed).toEqual([]);
  });

  it("adds a missing Russian form as a TODO from English _other", () => {
    const russian = {
      "files.count_one": entry("{{count}} файл"),
      "files.count_many": entry("{{count}} файлов"),
      "files.count_other": entry("{{count}} файла"),
      "files.title": entry("Файлы"),
    };
    const result = syncLocaleEntries(english, russian, "ru");
    expect(result.added).toEqual(["files.count_few"]);
    expect(result.entries["files.count_few"]).toEqual(
      entry("[TODO] {{count}} files", "count of files"),
    );
  });

  it.each(["zh", "ja", "ko"])("gives %s only the _other form", (locale) => {
    const catalog = {
      "files.count_other": entry("{{count}} x"),
      "files.title": entry("t"),
    };
    const result = syncLocaleEntries(english, catalog, locale);
    expect(result.added).toEqual([]);
    expect(result.removed).toEqual([]);
    expect(Object.keys(result.entries)).not.toContain("files.count_one");
  });

  it("removes a form the language never selects", () => {
    const chinese = {
      "files.count_one": entry("{{count}} 个文件"),
      "files.count_other": entry("{{count}} 个文件"),
      "files.title": entry("文件"),
    };
    expect(syncLocaleEntries(english, chinese, "zh").removed).toEqual([
      "files.count_one",
    ]);
  });

  it("still adds and removes plain keys", () => {
    const german = {
      "files.count_one": entry("{{count}} Datei"),
      "files.count_other": entry("{{count}} Dateien"),
      "files.gone": entry("Weg"),
    };
    const result = syncLocaleEntries(english, german, "de");
    expect(result.added).toEqual(["files.title"]);
    expect(result.entries["files.title"]).toEqual(entry("[TODO] Files"));
    expect(result.removed).toEqual(["files.gone"]);
    expect(result.entries).not.toHaveProperty("files.gone");
  });

  it("treats a suffix-like key without an _other sibling as a plain key", () => {
    const source = { "tour.step_one": entry("Step one") };
    const result = syncLocaleEntries(source, {}, "zh");
    expect(result.added).toEqual(["tour.step_one"]);
  });
});
