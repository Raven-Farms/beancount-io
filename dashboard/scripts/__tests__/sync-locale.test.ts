import { describe, expect, it } from "vitest";
import {
  editCatalogSource,
  ownCatalogKeys,
  syncLocaleEntries,
  type TranslationEntry,
} from "../lib/sync-locale";

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

// A sync edits only the entries it adds or removes; regenerating the file
// re-sorted and reformatted whole catalogs (w0/m3).
const catalog = `export interface TranslationEntry {
  message: string;
  description: string;
}

const deFiles: Record<string, TranslationEntry> = {
  "files.title": {
    message: "Dateien",
    description: "Page title",
  },
  "files.gone": {
    message: "Weg",
    description: "Removed upstream",
  },
  "files.count_other": {
    message: "{{count}} Dateien",
    description: "count of files",
  },
};

export default deFiles;
`;

describe("editCatalogSource", () => {
  it("cuts a removed entry and leaves every other line as it was", () => {
    const edited = editCatalogSource(catalog, {
      added: {},
      removed: ["files.gone"],
      order: ["files.title", "files.count_other"],
    });
    expect(edited).toBe(catalog.replace(/  "files\.gone"[\s\S]*?  \},\n/, ""));
  });

  it("inserts a new entry after its nearest English neighbour", () => {
    const edited = editCatalogSource(catalog, {
      added: { "files.count_one": entry("[TODO] {{count}} file", "count") },
      removed: [],
      order: ["files.title", "files.count_one", "files.count_other"],
    });
    expect(edited).toContain(
      `  "files.title": {
    message: "Dateien",
    description: "Page title",
  },
  "files.count_one": {
    message: "[TODO] {{count}} file",
    description: "count",
  },
  "files.gone": {`,
    );
  });

  it("puts a key with no earlier neighbour first in the object", () => {
    const edited = editCatalogSource(catalog, {
      added: { "files.aaa": entry("[TODO] A") },
      removed: [],
      order: ["files.aaa", "files.title"],
    });
    expect(edited).toContain(
      `const deFiles: Record<string, TranslationEntry> = {
  "files.aaa": {`,
    );
  });

  it("matches the indent of a catalog Prettier wrapped", () => {
    const wrapped = `const deReports: Record<string, { message: string; description: string }> =
  {
    "reports.title": {
      message: "Berichte",
      description: "Title",
    },
  };
`;
    const edited = editCatalogSource(wrapped, {
      added: { "reports.empty": entry("[TODO] Nothing") },
      removed: [],
      order: ["reports.title", "reports.empty"],
    });
    expect(edited).toContain(`    },
    "reports.empty": {
      message: "[TODO] Nothing",
      description: "d",
    },
  };`);
  });
});

describe("ownCatalogKeys", () => {
  it("lists the keys a file writes out, not the ones it spreads in", () => {
    const aggregate = `import deUpload from "../upload/locales/de";

const deEditor: Record<string, TranslationEntry> = {
  ...deUpload,
  "editor.title": {
    message: "Editor",
    description: "Title",
  },
};
`;
    expect([...ownCatalogKeys(aggregate)]).toEqual(["editor.title"]);
  });
});
