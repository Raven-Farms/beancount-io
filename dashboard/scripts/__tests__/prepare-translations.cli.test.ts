// @vitest-environment node
import { spawnSync } from "child_process";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { pluralCategories } from "../../src/i18n/plural";
import { EN_COMPARED_LOCALES } from "../../src/test/locale-scan";

// The real CLI, run on a fixture catalog tree (w0/m3): `--check` names each
// kind of drift and exits non-zero, a run fixes exactly that, and a second
// run changes nothing.
const SCRIPT = fileURLToPath(
  new URL("../prepare-translations.ts", import.meta.url),
);
const LOCALES_DIR = path.join("src", "features", "files", "locales");

let root: string;
const catalogPath = (locale: string) =>
  path.join(root, LOCALES_DIR, `${locale}.ts`);
const read = (locale: string) => fs.readFileSync(catalogPath(locale), "utf8");
const readAll = () =>
  Object.fromEntries(
    ["en", ...EN_COMPARED_LOCALES].map((locale) => [locale, read(locale)]),
  );

function run(...args: string[]) {
  // Inside the package, so `tsx`, the tsconfig paths and Prettier's config
  // resolve as they do for `yarn i18n:prepare`.
  return spawnSync(process.execPath, ["--import", "tsx", SCRIPT, ...args], {
    cwd: root,
    encoding: "utf8",
  });
}

function writeCatalog(locale: string, messages: Record<string, string>) {
  const name = `${locale}Files`;
  const entries = Object.entries(messages)
    .map(
      ([key, message]) =>
        `  ${JSON.stringify(key)}: {\n    message: ${JSON.stringify(message)},\n    description: "d",\n  },\n`,
    )
    .join("");
  fs.writeFileSync(
    catalogPath(locale),
    `const ${name} = {\n${entries}};\n\nexport default ${name};\n`,
  );
}

/** A locale's catalog in sync with English, in its own plural forms. */
function syncedMessages(locale: string): Record<string, string> {
  return {
    "files.title": `${locale}: Dateien`,
    ...Object.fromEntries(
      pluralCategories(locale).map((category) => [
        `files.count_${category}`,
        `${locale}: {{count}} ${category}`,
      ]),
    ),
  };
}

const problems = (output: string) =>
  output
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith(LOCALES_DIR))
    .sort();

describe("yarn i18n:prepare on a fixture tree", { timeout: 60_000 }, () => {
  beforeAll(() => {
    fs.mkdirSync(path.join(process.cwd(), "tmp"), { recursive: true });
    root = fs.mkdtempSync(path.join(process.cwd(), "tmp", "i18n-cli-"));
    fs.mkdirSync(path.join(root, LOCALES_DIR), { recursive: true });
    writeCatalog("en", {
      "files.title": "Files",
      "files.count_one": "{{count}} file",
      "files.count_other": "{{count}} files",
    });
    for (const locale of EN_COMPARED_LOCALES) {
      const messages = syncedMessages(locale);
      if (locale === "de") delete messages["files.title"];
      if (locale === "fr") messages["files.gone"] = "fr: parti";
      if (locale === "ru") delete messages["files.count_few"];
      if (locale === "es") messages["files.title"] = "[TODO] Files";
      writeCatalog(locale, messages);
    }
  });

  afterAll(() => fs.rmSync(root, { recursive: true, force: true }));

  it("--check names a missing key, an obsolete key, a lost plural form and a [TODO]", () => {
    const before = readAll();
    const check = run("--check");
    expect(check.status).toBe(1);
    expect(problems(check.stderr)).toEqual([
      `${LOCALES_DIR}/de.ts: missing files.title`,
      `${LOCALES_DIR}/es.ts: [TODO] files.title`,
      `${LOCALES_DIR}/fr.ts: obsolete files.gone`,
      `${LOCALES_DIR}/ru.ts: missing files.count_few`,
    ]);
    expect(readAll()).toEqual(before);
  });

  it("a run fixes exactly the drift and leaves every other catalog alone", () => {
    const before = readAll();
    expect(run().status).toBe(0);
    const after = readAll();

    expect(after.ru).toContain(`  "files.count_one": {
    message: "ru: {{count}} one",
    description: "d",
  },
  "files.count_few": {
    message: "[TODO] {{count}} files",
    description: "d",
  },
  "files.count_many": {`);
    expect(after.de).toContain('message: "[TODO] Files"');
    expect(after.fr).not.toContain("files.gone");
    const untouched = EN_COMPARED_LOCALES.filter(
      (locale) => !["de", "fr", "ru"].includes(locale),
    );
    for (const locale of ["en", ...untouched]) {
      expect(after[locale]).toBe(before[locale]);
    }

    // What remains is translation work, which --check still reports.
    const check = run("--check");
    expect(check.status).toBe(1);
    expect(problems(check.stderr)).toEqual([
      `${LOCALES_DIR}/de.ts: [TODO] files.title`,
      `${LOCALES_DIR}/es.ts: [TODO] files.title`,
      `${LOCALES_DIR}/ru.ts: [TODO] files.count_few`,
    ]);
  });

  it("a second run changes no file", () => {
    const before = readAll();
    expect(run().status).toBe(0);
    expect(readAll()).toEqual(before);
  });
});
