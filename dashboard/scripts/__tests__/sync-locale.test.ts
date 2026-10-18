import * as prettier from "prettier";
import { describe, expect, it } from "vitest";
import {
  catalogDrift,
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
// re-sorted and reformatted whole catalogs (w0/m3). Entries are found by
// parsing, so every catalog shape in the tree edits the same way.
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

/** The edit as `i18n:prepare` writes it: through Prettier. */
const edit = async (
  source: string,
  changes: Parameters<typeof editCatalogSource>[1],
) =>
  prettier.format(editCatalogSource(source, changes), {
    ...(await prettier.resolveConfig("src/features/x/locales/de.ts")),
    parser: "typescript",
  });

describe("editCatalogSource", () => {
  it("cuts a removed entry and leaves every other byte as it was", () => {
    const edited = editCatalogSource(catalog, {
      added: {},
      removed: ["files.gone"],
      order: ["files.title", "files.count_other"],
    });
    expect(edited).toBe(catalog.replace(/\n  "files\.gone"[\s\S]*?  \},/, ""));
  });

  it("inserts a new entry after its nearest neighbour", async () => {
    const edited = await edit(catalog, {
      added: { "files.count_one": entry("[TODO] {{count}} file", "count") },
      removed: [],
      order: ["files.title", "files.count_one", "files.count_other"],
    });
    expect(edited).toBe(
      catalog.replace(
        '  "files.gone": {',
        `  "files.count_one": {
    message: "[TODO] {{count}} file",
    description: "count",
  },
  "files.gone": {`,
      ),
    );
  });

  it("puts a key with no earlier neighbour first in the object", async () => {
    const edited = await edit(catalog, {
      added: { "files.aaa": entry("[TODO] A") },
      removed: [],
      order: ["files.aaa", "files.title"],
    });
    expect(edited).toContain(
      `const deFiles: Record<string, TranslationEntry> = {
  "files.aaa": {`,
    );
  });

  it("edits an untyped catalog that spreads a local object", async () => {
    // The shape of `reports/locales/*.ts`, which the layout regex refused.
    const reports = `import deExport from "../export/locales/de";

const deReportsShared = {
  "reports.shared": {
    message: "Geteilt",
    description: "d",
  },
};

const deReports = {
  ...deReportsShared,
  ...deExport,
  "reports.title": {
    message: "Berichte",
    description: "d",
  },
};

export default deReports;
`;
    expect([...ownCatalogKeys(reports)]).toEqual([
      "reports.title",
      "reports.shared",
    ]);
    const edited = await edit(reports, {
      added: { "reports.shared2": entry("[TODO] Shared too") },
      removed: [],
      order: ["reports.shared", "reports.shared2", "reports.title"],
    });
    expect(edited).toContain(`const deReportsShared = {
  "reports.shared": {
    message: "Geteilt",
    description: "d",
  },
  "reports.shared2": {
    message: "[TODO] Shared too",
    description: "d",
  },
};`);
  });

  it("adds to an aggregate that only spreads sub-catalogs", async () => {
    const aggregate = `import deDashboard from "../pages/dashboard/locales/de";

const deList = {
  ...deDashboard,
};

export default deList;
`;
    expect(ownCatalogKeys(aggregate).size).toBe(0);
    expect(
      await edit(aggregate, {
        added: { "list.empty": entry("[TODO] Nothing yet") },
        removed: [],
        order: ["list.empty"],
      }),
    ).toContain(`const deList = {
  "list.empty": {
    message: "[TODO] Nothing yet",
    description: "d",
  },
  ...deDashboard,
};`);
  });

  it("reads and removes a one-line entry like any other", () => {
    const oneLine = `const de = {
  "a.one": { message: "Eins", description: "d" },
  "a.two": {
    message: "Zwei",
    description: "d",
  },
};

export default de;
`;
    expect([...ownCatalogKeys(oneLine)]).toEqual(["a.one", "a.two"]);
    expect(
      editCatalogSource(oneLine, { added: {}, removed: ["a.one"], order: [] }),
    ).not.toContain("a.one");
  });
});

describe("ownCatalogKeys", () => {
  it("lists the keys a file writes out, not the ones it spreads in", () => {
    const aggregate = `import deUpload from "../upload/locales/de";

const deEditor: Record<string, { message: string; description: string }> = {
  ...deUpload,
  "editor.title": {
    message: "Editor",
    description: "Title",
  },
};

export default deEditor;
`;
    expect([...ownCatalogKeys(aggregate)]).toEqual(["editor.title"]);
  });
});

// `i18n:prepare --check` fails CI on each of these (w0/m3).
describe("catalogDrift", () => {
  const russian = {
    "files.count_one": entry("{{count}} файл"),
    "files.count_few": entry("{{count}} файла"),
    "files.count_many": entry("{{count}} файлов"),
    "files.count_other": entry("{{count}} файла"),
    "files.title": entry("Файлы"),
  };
  const without = (key: string) =>
    Object.fromEntries(Object.entries(russian).filter(([k]) => k !== key));

  it("finds nothing in a catalog that is in sync", () => {
    expect(catalogDrift(english, russian, "ru")).toEqual({
      missing: [],
      obsolete: [],
      todo: [],
    });
  });

  it("names a missing key", () => {
    expect(catalogDrift(english, without("files.title"), "ru").missing).toEqual(
      ["files.title"],
    );
  });

  it("names a deleted Russian plural form", () => {
    expect(
      catalogDrift(english, without("files.count_few"), "ru").missing,
    ).toEqual(["files.count_few"]);
  });

  it("names an obsolete key", () => {
    expect(
      catalogDrift(english, { ...russian, "files.gone": entry("x") }, "ru")
        .obsolete,
    ).toEqual(["files.gone"]);
  });

  it("names a message still marked [TODO]", () => {
    const drift = catalogDrift(
      english,
      { ...russian, "files.title": entry("  [TODO] Files") },
      "ru",
    );
    expect(drift.todo).toEqual(["files.title"]);
    expect(drift.missing).toEqual([]);
  });
});
