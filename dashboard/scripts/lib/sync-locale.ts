import { PLURAL_SUFFIX, pluralCategories } from "../../src/i18n/plural";

/** The prefix a key added by the sync carries until someone translates it. */
export const TODO_MARKER = "[TODO]";

export interface TranslationEntry {
  message: string;
  description: string;
}

/**
 * The plural family a key belongs to in `catalog`: its base when the key ends
 * in a CLDR suffix and the catalog also has `<base>_other`, else `null`.
 * `common.retry_one` with no `common.retry_other` is a plain key.
 */
function pluralBase(key: string, catalog: Record<string, unknown>) {
  const match = PLURAL_SUFFIX.exec(key);
  if (!match) return null;
  const base = key.slice(0, match.index);
  return `${base}_other` in catalog ? base : null;
}

/**
 * The keys `locale` needs for an English catalog with `sourceKeys`, each
 * paired with the English key it is translated from.
 *
 * A plural family expands into the categories `locale` uses rather than the
 * ones English uses: Russian keeps `_one`, `_few`, `_many` and `_other`, and
 * Chinese has `_other` only. A form English lacks is translated from
 * `_other`. Comparing key sets with English instead deleted every Russian
 * `_few` and gave Chinese a `_one` nothing selects (w0/m3).
 */
function expectedLocaleKeys(
  source: Record<string, unknown>,
  locale: string,
): Map<string, string> {
  const expected = new Map<string, string>();
  for (const key of Object.keys(source)) {
    const base = pluralBase(key, source);
    if (base === null) {
      expected.set(key, key);
      continue;
    }
    for (const category of pluralCategories(locale)) {
      const localeKey = `${base}_${category}`;
      expected.set(
        localeKey,
        localeKey in source ? localeKey : `${base}_other`,
      );
    }
  }
  return expected;
}

/**
 * `target` brought in line with `source` for `locale`: existing translations
 * kept, missing keys added as `[TODO] <English>`, keys `locale` does not need
 * dropped.
 */
export function syncLocaleEntries(
  source: Record<string, TranslationEntry>,
  target: Record<string, TranslationEntry>,
  locale: string,
): {
  entries: Record<string, TranslationEntry>;
  added: string[];
  removed: string[];
} {
  const expected = expectedLocaleKeys(source, locale);
  const entries: Record<string, TranslationEntry> = {};
  const added: string[] = [];
  for (const [key, sourceKey] of expected) {
    if (target[key]) {
      entries[key] = target[key];
      continue;
    }
    const { message, description } = source[sourceKey];
    entries[key] = { message: `${TODO_MARKER} ${message}`, description };
    added.push(key);
  }
  const removed = Object.keys(target).filter((key) => !expected.has(key));
  return { entries, added, removed };
}

/**
 * What syncing `target` would change, without changing it: keys `locale` is
 * missing (its own plural forms included), keys it no longer needs, and
 * messages still marked `[TODO]`. All empty when the catalog is in sync.
 */
export function catalogDrift(
  source: Record<string, TranslationEntry>,
  target: Record<string, TranslationEntry>,
  locale: string,
): { missing: string[]; obsolete: string[]; todo: string[] } {
  const { added, removed } = syncLocaleEntries(source, target, locale);
  const todo = Object.keys(target).filter(
    (key) =>
      !removed.includes(key) &&
      target[key].message.trimStart().startsWith(TODO_MARKER),
  );
  return { missing: added, obsolete: removed, todo };
}

const escapeRegExp = (text: string) =>
  text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/**
 * Keys a catalog file writes out itself. An aggregate catalog also spreads
 * its sub-features' catalogs in; those keys belong to the sub-feature's own
 * file, which the sync edits in its turn.
 */
export function ownCatalogKeys(source: string): Set<string> {
  return new Set(
    Array.from(
      source.matchAll(/^ +("(?:[^"\\]|\\.)*"): \{$/gm),
      (match) => JSON.parse(match[1]) as string,
    ),
  );
}

/** Where `key`'s `"key": { … },` block sits in a Prettier-formatted catalog. */
function entrySpan(source: string, key: string) {
  const match = new RegExp(
    `^( +)${escapeRegExp(JSON.stringify(key))}: \\{\\n[\\s\\S]*?^\\1\\},\\n`,
    "m",
  ).exec(source);
  return match
    ? {
        start: match.index,
        end: match.index + match[0].length,
        indent: match[1],
      }
    : null;
}

/** Just inside the catalog object's opening brace, and its entries' indent. */
function objectStart(source: string) {
  const match = /^const \w+:[^=]*=\s*\{\n/m.exec(source);
  if (!match) {
    throw new Error("catalog has no `const …: Record<…> = {` declaration");
  }
  const at = match.index + match[0].length;
  return { at, indent: /^ +/.exec(source.slice(at))?.[0] ?? "  " };
}

const renderEntry = (
  indent: string,
  key: string,
  { message, description }: TranslationEntry,
) =>
  `${indent}${JSON.stringify(key)}: {\n` +
  `${indent}  message: ${JSON.stringify(message)},\n` +
  `${indent}  description: ${JSON.stringify(description)},\n` +
  `${indent}},\n`;

/**
 * A catalog file's text with `removed` entries cut out and `added` ones
 * inserted, every other byte untouched. Each new entry goes after the nearest
 * key before it in `order` (the English catalog's), else first in the object.
 * Regenerating the file instead re-sorted and reformatted whole catalogs, so
 * adding one key showed up as hundreds of changed lines (w0/m3). Run Prettier
 * over the result for long messages.
 */
export function editCatalogSource(
  source: string,
  changes: {
    added: Record<string, TranslationEntry>;
    removed: readonly string[];
    order: readonly string[];
  },
): string {
  let text = source;
  for (const key of changes.removed) {
    const span = entrySpan(text, key);
    if (span) text = text.slice(0, span.start) + text.slice(span.end);
  }
  for (const [index, key] of changes.order.entries()) {
    const entry = changes.added[key];
    if (!entry) continue;
    const before = changes.order
      .slice(0, index)
      .reverse()
      .map((previous) => entrySpan(text, previous))
      .find((span) => span !== null);
    const { at, indent } = before
      ? { at: before.end, indent: before.indent }
      : objectStart(text);
    text = text.slice(0, at) + renderEntry(indent, key, entry) + text.slice(at);
  }
  return text;
}
