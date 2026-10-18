#!/usr/bin/env tsx

// Prepare translation files for translators (Feature-Based Architecture)
// This script:
// 1. Extracts all translation keys from source code (t("key") calls)
// 2. Adds missing keys to en.ts files with auto-generated messages
// 3. Syncs en.ts to other languages with [TODO] prefix
// 4. Removes unused translation keys that don't exist in en.ts
// 5. Reports translation status
// Works with the feature-based locale structure in src/features/X/locales/

import * as fs from "fs";
import * as path from "path";
import * as prettier from "prettier";
import { SUPPORTED_LANGUAGES } from "../src/i18n/config";
import { catalogStatus, type CatalogStatus } from "./lib/catalog-status";
import {
  catalogDrift,
  editCatalogSource,
  ownCatalogKeys,
  syncLocaleEntries,
  TODO_MARKER,
  type TranslationEntry,
} from "./lib/sync-locale";

const SRC_DIR = path.join(process.cwd(), "src");
const FEATURES_DIR = path.join(SRC_DIR, "features");
// The shared catalogs do not live under `features/`. `common` holds the
// `common.*` and `component.*` keys, `seo` the `seo.*` ones, and both sit
// under `i18n/locales/`. Pointing at `src/common/locales` made this script
// crash on startup, so it had not run for either of them.
const SHARED_LOCALE_DIRS: Record<string, string> = {
  common: path.join(SRC_DIR, "i18n", "locales", "common"),
  seo: path.join(SRC_DIR, "i18n", "locales", "seo"),
};

// Every supported language but English, from the canonical list: a hand-kept
// copy here had fallen behind it and left Japanese and Korean unsynced.
const TARGET_LOCALES = SUPPORTED_LANGUAGES.filter((locale) => locale !== "en");

interface FeatureStats extends CatalogStatus {
  feature: string;
  locale: string;
}

interface GlobalStats {
  locale: string;
  completed: number;
  total: number;
  percentage: number;
  todoCount: number;
}

/** A catalog's structured entries as `key → message`. */
function messagesOf(
  translations: Record<string, unknown>,
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(translations).flatMap(([key, value]) =>
      isStructuredFormat(value) ? [[key, value.message]] : [],
    ),
  );
}

/**
 * Check if a value is in structured format
 */
function isStructuredFormat(value: unknown): value is TranslationEntry {
  return (
    typeof value === "object" &&
    value !== null &&
    "message" in value &&
    typeof value.message === "string" &&
    "description" in value &&
    typeof value.description === "string"
  );
}

/**
 * Read translations from a TypeScript file
 */
async function readTranslations(
  filePath: string,
): Promise<Record<string, TranslationEntry>> {
  if (!fs.existsSync(filePath)) {
    return {};
  }

  try {
    // Use dynamic import to load the TypeScript module
    // Add timestamp to bust Node.js module cache for repeated reads
    const absolutePath = path.resolve(filePath);
    const fileUrl = `file://${absolutePath}?t=${Date.now()}`;
    const module = await import(fileUrl);
    const translations = module.default || module;

    // Validate structure
    const validated: Record<string, TranslationEntry> = {};
    for (const [key, value] of Object.entries(translations)) {
      if (isStructuredFormat(value)) {
        validated[key] = value;
      }
    }

    return validated;
  } catch (error) {
    console.error(`  ⚠️  Error reading ${filePath}:`, error);
    return {};
  }
}

/** A new catalog file's text, its entries in the order given. */
function renderCatalog(
  filePath: string,
  translations: Record<string, TranslationEntry>,
  locale: string,
): string {
  // Extract variable name from existing file or create new one
  const feature = path.basename(path.dirname(path.dirname(filePath)));

  // Determine variable name based on feature
  let varName: string;
  if (feature === "common" || feature === "locales") {
    varName = `${locale}Common`;
  } else {
    // Convert feature name to camelCase
    const camelFeature = feature
      .split("-")
      .map((part, index) =>
        index === 0 ? part : part.charAt(0).toUpperCase() + part.slice(1),
      )
      .join("");
    varName = `${locale}${camelFeature.charAt(0).toUpperCase() + camelFeature.slice(1)}`;
  }

  // Build file content
  let content = `export interface TranslationEntry {\n`;
  content += `  message: string;\n`;
  content += `  description: string;\n`;
  content += `}\n\n`;
  content += `const ${varName}: Record<string, TranslationEntry> = {\n`;

  for (const [key, entry] of Object.entries(translations)) {
    content += `  "${key}": {\n`;
    content += `    message: ${JSON.stringify(entry.message)},\n`;
    content += `    description: ${JSON.stringify(entry.description)},\n`;
    content += `  },\n`;
  }

  content += `};\n\n`;
  content += `export default ${varName};\n`;
  return content;
}

/**
 * Write a catalog's changes. An existing file is edited in place — removed
 * entries cut, added ones inserted beside their neighbours, every other line
 * untouched — and a missing one is generated; either way the result is
 * formatted as the repository's Prettier config formats it. Regenerating
 * existing files re-sorted and reformatted them, so one new key showed up as
 * hundreds of changed lines (w0/m3).
 */
async function saveCatalog(
  filePath: string,
  locale: string,
  entries: Record<string, TranslationEntry>,
  changes: { added: readonly string[]; removed: readonly string[] },
): Promise<void> {
  const text = fs.existsSync(filePath)
    ? editCatalogSource(fs.readFileSync(filePath, "utf8"), {
        added: Object.fromEntries(
          changes.added.map((key) => [key, entries[key]]),
        ),
        removed: changes.removed,
        order: Object.keys(entries),
      })
    : renderCatalog(filePath, entries, locale);
  const options = await prettier.resolveConfig(filePath);
  fs.writeFileSync(
    filePath,
    await prettier.format(text, { ...options, filepath: filePath }),
    "utf8",
  );
}

/** The entries of `translations` a catalog file writes out itself. */
function ownEntries(
  translations: Record<string, TranslationEntry>,
  filePath: string,
): Record<string, TranslationEntry> {
  if (!fs.existsSync(filePath)) return {};
  const own = ownCatalogKeys(fs.readFileSync(filePath, "utf8"));
  return Object.fromEntries(
    Object.entries(translations).filter(([key]) => own.has(key)),
  );
}

/**
 * Sync translations from source (en) to target locale
 * - Add missing keys with [TODO] prefix
 * - Remove keys the locale does not need, keeping its own plural forms
 */
/**
 * A feature's English catalog and one locale's, as the entries each file
 * writes out itself: an aggregate catalog's spread-in keys are synced and
 * checked through the sub-feature's own file. `null` without an English file.
 */
async function readCatalogPair(feature: string, locale: string) {
  const sourcePath = getLocaleFilePath(feature, "en");
  const targetPath = getLocaleFilePath(feature, locale);
  const source = ownEntries(await readTranslations(sourcePath), sourcePath);
  if (Object.keys(source).length === 0) return null;
  const target = ownEntries(await readTranslations(targetPath), targetPath);
  return { source, target, targetPath };
}

async function syncTranslations(
  feature: string,
  locale: string,
): Promise<{ added: number; removed: number }> {
  const pair = await readCatalogPair(feature, locale);
  if (!pair) return { added: 0, removed: 0 };
  const { source, target, targetPath } = pair;
  const { entries, added, removed } = syncLocaleEntries(source, target, locale);

  // If no changes needed, skip
  if (added.length === 0 && removed.length === 0) {
    return { added: 0, removed: 0 };
  }

  await saveCatalog(targetPath, locale, entries, { added, removed });

  return { added: added.length, removed: removed.length };
}

/**
 * Get all feature directories
 */
function getFeatureDirectories(): string[] {
  const features: string[] = [];

  // The shared catalogs are deliberately absent. See
  // `SHARED_LOCALE_DIRS` and `getReportedFeatures`.

  // Scan the features directory. It nests: `git/commits/locales` and
  // `ledger-data/statistics/locales` are as real as `journal/locales`, and a
  // single-level scan left both invisible to this script.
  const walk = (dir: string, prefix: string) => {
    if (!fs.existsSync(dir)) return;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!entry.isDirectory() || entry.name === "locales") continue;
      const name = prefix ? `${prefix}/${entry.name}` : entry.name;
      if (fs.existsSync(path.join(dir, entry.name, "locales"))) {
        features.push(name);
      }
      walk(path.join(dir, entry.name), name);
    }
  };
  walk(FEATURES_DIR, "");

  return features.sort();
}

/**
 * Get locale file path for a feature
 */
function getLocaleFilePath(feature: string, locale: string): string {
  const shared = SHARED_LOCALE_DIRS[feature];
  if (shared) {
    return path.join(shared, `${locale}.ts`);
  }
  return path.join(FEATURES_DIR, feature, "locales", `${locale}.ts`);
}

/**
 * The features the status report covers: everything under `features/`, plus
 * the shared catalogs.
 *
 * Kept separate from `getFeatureDirectories`, which drives the steps that
 * *write*. Those must not reach the shared catalogs: `determineFeatureFromKey`
 * treats `common` as the home for any key it cannot attribute, so pointing the
 * sync at it rewrites the file with every key in the codebase — 40k lines of
 * auto-generated English, including one literal `${key}` from a template bug.
 * That stayed hidden because the script crashed before reaching it, the path
 * having pointed at `src/common/locales`, which does not exist.
 */
function getReportedFeatures(): string[] {
  const shared = Object.entries(SHARED_LOCALE_DIRS)
    .filter(([, dir]) => fs.existsSync(dir))
    .map(([name]) => name);
  return [...getFeatureDirectories(), ...shared].sort();
}

/**
 * Keys this locale has left ending in verbatim English, compared against the
 * same key in `en`. Uses the predicate the guard uses, so the script and
 * `src/test/locale-stray-english.test.ts` cannot disagree about what counts.
 */
/**
 * Analyze a single feature locale
 */
async function analyzeFeatureLocale(
  feature: string,
  locale: string,
): Promise<FeatureStats | null> {
  const filePath = getLocaleFilePath(feature, locale);

  if (!fs.existsSync(filePath)) {
    return null;
  }

  const messages = messagesOf(await readTranslations(filePath));
  const english = messagesOf(
    await readTranslations(getLocaleFilePath(feature, "en")),
  );
  return { feature, locale, ...catalogStatus(messages, english, locale) };
}

/**
 * Generate a human-readable message from a translation key
 * Examples:
 *   "uploadFiles" -> "Upload Files"
 *   "relatedLinks.uploadFiles" -> "Upload Files"
 *   "auth.login" -> "Login"
 */
function generateMessageFromKey(key: string): string {
  // Get the last part of the key (after the last dot)
  const lastPart = key.split(".").pop() || key;

  // Convert camelCase to Title Case
  const words = lastPart
    .replace(/([A-Z])/g, " $1") // Add space before capital letters
    .split(/[\s_-]+/) // Split on spaces, underscores, or hyphens
    .filter((w) => w.length > 0)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());

  return words.join(" ");
}

/**
 * Determine which feature a translation key belongs to
 * Based on namespace prefix (e.g., "auth.login" -> "auth")
 * Falls back to "common" for keys without clear namespace
 */
/**
 * Which catalog already holds each key, read from the English files.
 *
 * This is the reliable way to place a key, because the namespace does not
 * name the directory: `aiAgent.*` lives in `ai-agent/`, `userSettings.*` in
 * `user-settings/`, and `page.*` and `component.*` are spread across most
 * features and the shared catalog. Matching on the namespace alone left 823
 * of 1421 keys unplaced.
 */
async function buildKeyIndex(features: string[]): Promise<Map<string, string>> {
  const index = new Map<string, string>();
  for (const feature of features) {
    const englishPath = getLocaleFilePath(feature, "en");
    if (!fs.existsSync(englishPath)) continue;
    for (const key of Object.keys(await readTranslations(englishPath))) {
      if (!index.has(key)) index.set(key, feature);
    }
  }
  return index;
}

function determineFeatureFromKey(
  key: string,
  features: string[],
  keyIndex?: Map<string, string>,
): string | null {
  const known = keyIndex?.get(key);
  if (known) return known;

  for (const feature of features) {
    if (key.startsWith(`${feature}.`)) {
      return feature;
    }
  }

  // No guess. The previous fallback was `common`, which meant every key whose
  // namespace does not match a directory — `aiAgent.*`, `page.*`, `seo.*` —
  // was written into the shared catalog as auto-generated English.
  return null;
}

/**
 * Recursively find all TypeScript files in a directory
 * Excludes tests, locales, node_modules, and generated files
 */
function findTypeScriptFiles(dir: string, fileList: string[] = []): string[] {
  const files = fs.readdirSync(dir, { withFileTypes: true });

  for (const file of files) {
    const filePath = path.join(dir, file.name);

    // Skip excluded directories
    if (
      file.isDirectory() &&
      !file.name.includes("node_modules") &&
      !file.name.includes("locales") &&
      !file.name.includes("generated-graphql") &&
      !file.name.includes("__tests__")
    ) {
      findTypeScriptFiles(filePath, fileList);
    } else if (
      file.isFile() &&
      (file.name.endsWith(".ts") || file.name.endsWith(".tsx")) &&
      !file.name.includes(".test.")
    ) {
      fileList.push(filePath);
    }
  }

  return fileList;
}

/**
 * Extract all translation keys from source code
 * Scans .ts and .tsx files for t("key") and t('key') calls
 */
async function extractKeysFromCode(): Promise<{
  keysByFeature: Map<string, Set<string>>;
  unattributed: Set<string>;
}> {
  const keysByFeature = new Map<string, Set<string>>();
  const unattributed = new Set<string>();
  const allFeatures = getReportedFeatures();
  const keyIndex = await buildKeyIndex(allFeatures);

  // Find all TypeScript files in src directory
  const files = findTypeScriptFiles(SRC_DIR);

  // Regex to match t("key") or t('key') calls
  // Captures the key inside the quotes
  const tCallRegex = /\bt\(["']([^"']+)["']\)/g;

  for (const file of files) {
    const content = fs.readFileSync(file, "utf8");
    const matches = content.matchAll(tCallRegex);

    for (const match of matches) {
      const key = match[1];

      // The regex reads source as text, so it also matches a string that
      // *describes* a call rather than being one — `use-translations.ts`
      // formats its own error as `t("${key}")`. A template placeholder can
      // never be a literal key, so the capture is not one either.
      if (key.includes("${")) continue;

      const feature = determineFeatureFromKey(key, allFeatures, keyIndex);

      // A key that belongs to no feature is reported, not written. Writing it
      // to `common` filed `aiAgent.attachFile` under the shared catalog.
      if (feature === null) {
        unattributed.add(key);
        continue;
      }

      if (!keysByFeature.has(feature)) {
        keysByFeature.set(feature, new Set());
      }
      keysByFeature.get(feature)!.add(key);
    }
  }

  return { keysByFeature, unattributed };
}

/**
 * Add missing keys to English locale files
 * Returns count of keys added per feature
 */
/** Keys code uses for `feature` that its English catalog does not define. */
function missingEnglishKeys(
  feature: string,
  keys: Set<string>,
  english: Record<string, TranslationEntry>,
): string[] {
  // `determineFeatureFromKey` returns `common` for any key it cannot
  // attribute, so this would otherwise write every unattributed key in the
  // codebase into the shared catalog. They are read-only here.
  if (feature in SHARED_LOCALE_DIRS) return [];
  return Array.from(keys).filter((key) => !(key in english));
}

/**
 * `--check`: what a run would change, without writing anything — keys code
 * uses that English lacks, keys a locale is missing (its own plural forms
 * included) or no longer needs — plus messages still marked `[TODO]`. Lists
 * each, and returns the exit code: non-zero on any, so CI keeps
 * `yarn i18n:prepare` a no-op on main (w0/m3).
 */
async function checkCatalogs(): Promise<number> {
  const offenders: string[] = [];
  const { keysByFeature } = await extractKeysFromCode();
  for (const [feature, keys] of keysByFeature) {
    const english = await readTranslations(getLocaleFilePath(feature, "en"));
    for (const key of missingEnglishKeys(feature, keys, english)) {
      offenders.push(`en · ${feature}: ${key} is used in code but missing`);
    }
  }
  const features = getFeatureDirectories();
  for (const locale of TARGET_LOCALES) {
    for (const feature of features) {
      const pair = await readCatalogPair(feature, locale);
      if (!pair) continue;
      const drift = catalogDrift(pair.source, pair.target, locale);
      const where = path.relative(process.cwd(), pair.targetPath);
      for (const key of drift.missing)
        offenders.push(`${where}: missing ${key}`);
      for (const key of drift.obsolete) {
        offenders.push(`${where}: obsolete ${key}`);
      }
      for (const key of drift.todo) offenders.push(`${where}: [TODO] ${key}`);
    }
  }
  if (offenders.length === 0) {
    console.log("✅ Translation catalogs are in sync.");
    return 0;
  }
  console.error(`❌ ${offenders.length} translation catalog problem(s):\n`);
  for (const offender of offenders) console.error(`   ${offender}`);
  console.error(
    "\nRun `yarn i18n:prepare` to add and remove keys, then translate every [TODO].",
  );
  return 1;
}

async function addMissingKeysToEnglish(
  extractedKeys: Map<string, Set<string>>,
): Promise<Map<string, number>> {
  const addedCounts = new Map<string, number>();

  for (const [feature, keys] of extractedKeys.entries()) {
    const enPath = getLocaleFilePath(feature, "en");
    const existingTranslations = await readTranslations(enPath);
    const missingKeys = missingEnglishKeys(feature, keys, existingTranslations);

    if (missingKeys.length === 0) {
      continue;
    }

    // Add missing keys to translations
    const updatedTranslations = { ...existingTranslations };

    for (const key of missingKeys) {
      updatedTranslations[key] = {
        message: generateMessageFromKey(key),
        description: "Auto-generated from code usage",
      };
    }

    await saveCatalog(enPath, "en", updatedTranslations, {
      added: missingKeys,
      removed: [],
    });

    addedCounts.set(feature, missingKeys.length);
  }

  return addedCounts;
}

/**
 * Main function
 */
async function main() {
  if (process.argv.includes("--check")) {
    process.exitCode = await checkCatalogs();
    return;
  }

  console.log(
    "🌍 Translation Preparation & Sync (Feature-Based Architecture)\n",
  );
  console.log("=".repeat(80));

  const features = getFeatureDirectories();
  console.log(`\n📁 Found ${features.length} features with locales:\n`);
  console.log(`   ${features.join(", ")}\n`);

  // Step 1: Extract translation keys from code
  console.log("\n🔍 Step 1: Extracting translation keys from code...\n");
  const { keysByFeature: extractedKeys, unattributed } =
    await extractKeysFromCode();

  // Count total keys
  let totalKeysFound = 0;
  for (const keys of extractedKeys.values()) {
    totalKeysFound += keys.size;
  }
  console.log(`   Found ${totalKeysFound} unique translation keys in code\n`);

  if (unattributed.size > 0) {
    console.log(
      `   ⚠️  ${unattributed.size} key(s) match no feature directory and were not written:\n`,
    );
    for (const key of Array.from(unattributed).sort()) {
      console.log(`      ${key}`);
    }
    console.log(
      "\n   These live in a shared catalog. Add them there by hand rather than",
    );
    console.log("   letting this script invent an English message for them.\n");
  }

  // Step 2: Add missing keys to English locale files
  console.log("📝 Step 2: Adding missing keys to en.ts files...\n");
  const addedCounts = await addMissingKeysToEnglish(extractedKeys);

  if (addedCounts.size === 0) {
    console.log("   ✅ All keys already exist in en.ts files!");
  } else {
    for (const [feature, count] of addedCounts.entries()) {
      console.log(`   ${feature}: +${count} key(s) added`);
    }
  }

  // Step 3: Sync all translations (add missing, remove unused)
  console.log("\n🔄 Step 3: Syncing translation files to other languages...\n");

  let totalAdded = 0;
  let totalRemoved = 0;

  for (const locale of TARGET_LOCALES) {
    let localeAdded = 0;
    let localeRemoved = 0;

    for (const feature of features) {
      const { added, removed } = await syncTranslations(feature, locale);
      localeAdded += added;
      localeRemoved += removed;
    }

    if (localeAdded > 0 || localeRemoved > 0) {
      const changes = [];
      if (localeAdded > 0) changes.push(`+${localeAdded} added`);
      if (localeRemoved > 0) changes.push(`-${localeRemoved} removed`);
      console.log(`   ${locale.toUpperCase()}: ${changes.join(", ")}`);
    }

    totalAdded += localeAdded;
    totalRemoved += localeRemoved;
  }

  if (totalAdded === 0 && totalRemoved === 0) {
    console.log("   ✅ All translations are already in sync!");
  } else {
    console.log(
      `\n   📝 Summary: ${totalAdded} keys added, ${totalRemoved} keys removed`,
    );
  }

  // Step 2: Analyze all features and locales, including the shared catalogs,
  // which the write steps above deliberately leave alone.
  const reportedFeatures = getReportedFeatures();
  console.log("\n" + "=".repeat(80));
  console.log("\n📊 Translation Status Report\n");

  const allStats: FeatureStats[] = [];

  for (const locale of TARGET_LOCALES) {
    console.log(`\n🔍 Analyzing ${locale.toUpperCase()} translations...\n`);

    for (const feature of reportedFeatures) {
      const stats = await analyzeFeatureLocale(feature, locale);
      if (stats) {
        allStats.push(stats);

        const status =
          stats.halfTranslated.length > 0 || stats.copiedWhole.length > 0
            ? "⚠️ "
            : stats.percentage === 100
              ? "✅"
              : "📝";
        const progressBar =
          "█".repeat(Math.floor(stats.percentage / 5)) +
          "░".repeat(20 - Math.floor(stats.percentage / 5));

        console.log(
          `   ${status} ${feature.padEnd(20)} | ${String(stats.completed).padStart(3)}/${String(stats.total).padStart(3)} | ${progressBar} ${stats.percentage}%${stats.todoCount > 0 ? ` (${stats.todoCount} TODOs)` : ""}${stats.halfTranslated.length > 0 ? ` ⚠️  ${stats.halfTranslated.length} half-translated` : ""}${stats.copiedWhole.length > 0 ? ` ⚠️  ${stats.copiedWhole.length} copied from English` : ""}`,
        );
      }
    }
  }

  // Half-translated keys, named so they can be opened and fixed. A key like
  // this is the residue of editing a `[TODO]` line and replacing only its
  // first word, so it counts as completed above while reading as neither
  // language.
  const halfTranslated = allStats.filter((s) => s.halfTranslated.length > 0);
  if (halfTranslated.length > 0) {
    console.log("\n" + "=".repeat(80));
    console.log("\n⚠️  Half-translated messages\n");
    console.log(
      "   These end in verbatim English. They are not counted as TODOs,",
    );
    console.log("   so nothing else in this report flags them.\n");
    for (const stats of halfTranslated) {
      console.log(`   ${stats.locale} · ${stats.feature}`);
      for (const key of stats.halfTranslated) {
        console.log(`      ${key}`);
      }
    }
  }

  // Messages pasted whole from English, named so they can be translated.
  // They are not counted as completed above; CI rejects them too
  // (`locale-stray-english.test.ts`), with the same allowlist.
  const copiedWhole = allStats.filter((s) => s.copiedWhole.length > 0);
  if (copiedWhole.length > 0) {
    console.log("\n" + "=".repeat(80));
    console.log("\n⚠️  Messages copied whole from English\n");
    console.log("   Translate each, or add it to IDENTICAL_BY_DESIGN in");
    console.log(
      "   src/test/locale-scan.ts with the reason it is correct in English.\n",
    );
    for (const stats of copiedWhole) {
      console.log(`   ${stats.locale} · ${stats.feature}`);
      for (const key of stats.copiedWhole) {
        console.log(`      ${key}`);
      }
    }
  }

  // Calculate global stats per locale
  console.log("\n" + "=".repeat(80));
  console.log("\n📊 Overall Translation Progress by Locale:\n");
  console.log("  Locale | Completed | Total | Progress");
  console.log("  -------|-----------|-------|----------");

  const globalStats: GlobalStats[] = [];

  for (const locale of TARGET_LOCALES) {
    const localeStats = allStats.filter((s) => s.locale === locale);
    const total = localeStats.reduce((sum, s) => sum + s.total, 0);
    const completed = localeStats.reduce((sum, s) => sum + s.completed, 0);
    const todoCount = localeStats.reduce((sum, s) => sum + s.todoCount, 0);
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 100;

    globalStats.push({
      locale,
      completed,
      total,
      percentage,
      todoCount,
    });

    const progressBar =
      "█".repeat(Math.floor(percentage / 5)) +
      "░".repeat(20 - Math.floor(percentage / 5));
    const status = percentage === 100 ? "✅" : "📝";
    console.log(
      `  ${status} ${locale.padEnd(4)} | ${String(completed).padStart(9)} | ${String(total).padStart(5)} | ${progressBar} ${percentage}%${todoCount > 0 ? ` (${todoCount} TODOs)` : ""}`,
    );
  }

  // Find locales with TODOs
  const localesWithTodos = globalStats.filter((s) => s.todoCount > 0);

  if (localesWithTodos.length > 0) {
    console.log("\n" + "=".repeat(80));
    console.log("\n📝 Locales with TODO items:\n");

    for (const { locale, todoCount } of localesWithTodos) {
      console.log(`   ${locale.toUpperCase()}: ${todoCount} TODOs remaining`);

      // Show which features have TODOs
      const featureTodos = allStats
        .filter((s) => s.locale === locale && s.todoCount > 0)
        .map((s) => `${s.feature} (${s.todoCount})`);

      console.log(`      → ${featureTodos.join(", ")}\n`);
    }
  }

  console.log("\n" + "=".repeat(80));
  console.log("\n✨ Translation status report complete!\n");
  console.log("📝 How to translate:");
  console.log("   1. Navigate to src/features/<feature>/locales/<locale>.ts");
  console.log(
    "   2. Or src/i18n/locales/common/<locale>.ts for common.* and component.* keys",
  );
  console.log('   3. Search for "[TODO]" to find untranslated keys');
  console.log('   4. Replace "[TODO] English text" with translated text');
  console.log(
    "   5. Translate anything listed above as half-translated or copied",
  );
  console.log("   6. Keep the description field unchanged");
  console.log(
    "   7. Run `yarn i18n:check` — it fails while any [TODO] or drift remains\n",
  );
  console.log(
    "💡 Tip: Use \"grep -n '\\[TODO\\]' $(find src -path '*/locales/*' -name <locale>.ts)\" to find pending translations\n",
  );
}

main();
