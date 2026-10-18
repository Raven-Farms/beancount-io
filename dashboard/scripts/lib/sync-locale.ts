import ts from "typescript";
import { pluralCategories, pluralFamily } from "../../src/i18n/plural";
import type { TranslationEntry } from "../../src/i18n/utils";
import { TODO_MARKER, isTodoMessage } from "../../src/test/locale-scan";

export type { TranslationEntry };

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
  const categories = pluralCategories(locale);
  const expected = new Map<string, string>();
  for (const key of Object.keys(source)) {
    const base = pluralFamily(key, (other) => other in source);
    if (base === null) {
      expected.set(key, key);
      continue;
    }
    for (const category of categories) {
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
 * dropped. `entries` is in the locale's expected order.
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
  const obsolete = new Set(removed);
  const todo = Object.keys(target).filter(
    (key) => !obsolete.has(key) && isTodoMessage(target[key].message),
  );
  return { missing: added, obsolete: removed, todo };
}

/** `{ … }`, unwrapped from `as`, `satisfies` or parentheses. */
function objectLiteral(node: ts.Expression | undefined) {
  while (
    node &&
    (ts.isAsExpression(node) ||
      ts.isSatisfiesExpression(node) ||
      ts.isParenthesizedExpression(node))
  ) {
    node = node.expression;
  }
  return node && ts.isObjectLiteralExpression(node) ? node : undefined;
}

/**
 * The object literals a catalog file writes its own entries into: the one
 * it exports by default, then any local `const` object that one spreads in
 * (`reports` keeps shared keys in `deReportsShared`). Spreads of imported
 * catalogs are not followed; their keys belong to the sub-feature's file.
 * Empty when the default export is not an object literal — `reports/export`
 * builds its catalog with a function, so it has no entries to edit.
 */
function ownObjects(file: ts.SourceFile): ts.ObjectLiteralExpression[] {
  const locals = new Map<string, ts.ObjectLiteralExpression>();
  let exported: ts.Expression | undefined;
  for (const statement of file.statements) {
    if (ts.isVariableStatement(statement)) {
      for (const declaration of statement.declarationList.declarations) {
        const object = objectLiteral(declaration.initializer);
        if (object && ts.isIdentifier(declaration.name)) {
          locals.set(declaration.name.text, object);
        }
      }
    } else if (ts.isExportAssignment(statement)) {
      exported = statement.expression;
    }
  }
  const root =
    exported && ts.isIdentifier(exported)
      ? locals.get(exported.text)
      : objectLiteral(exported);
  if (!root) return [];
  const objects = [root];
  for (const object of objects) {
    for (const property of object.properties) {
      if (
        ts.isSpreadAssignment(property) &&
        ts.isIdentifier(property.expression)
      ) {
        const local = locals.get(property.expression.text);
        if (local && !objects.includes(local)) objects.push(local);
      }
    }
  }
  return objects;
}

interface CatalogSlot {
  /** Where the entry begins, its leading comments included. */
  start: number;
  /** Just past the entry, and past the comma after it when there is one. */
  end: number;
  hasComma: boolean;
}

/**
 * Every entry a catalog file writes out itself, by message key, and where a
 * new first entry goes. Parsed with the TypeScript compiler rather than
 * matched by layout, so a one-line entry, an untyped `const` or an aggregate
 * that only spreads sub-catalogs reads like any other catalog.
 */
function parseCatalog(source: string) {
  const file = ts.createSourceFile(
    "catalog.ts",
    source,
    ts.ScriptTarget.Latest,
  );
  const objects = ownObjects(file);
  const entries = new Map<string, CatalogSlot>();
  for (const object of objects) {
    for (const property of object.properties) {
      if (
        !ts.isPropertyAssignment(property) ||
        !(
          ts.isStringLiteral(property.name) || ts.isIdentifier(property.name)
        ) ||
        !ts.isObjectLiteralExpression(property.initializer)
      ) {
        continue;
      }
      const comma = /^\s*,/.exec(source.slice(property.end));
      entries.set(property.name.text, {
        start: property.getFullStart(),
        end: property.end + (comma?.[0].length ?? 0),
        hasComma: comma !== null,
      });
    }
  }
  // Just inside the default-exported object's opening brace.
  const firstSlot = objects[0] ? objects[0].getStart(file) + 1 : undefined;
  return { entries, firstSlot };
}

/** Keys a catalog file writes out itself, not the ones it spreads in. */
export function ownCatalogKeys(source: string): Set<string> {
  return new Set(parseCatalog(source).entries.keys());
}

// Laid out by Prettier afterwards; the line breaks keep it multi-line.
const renderEntry = (key: string, { message, description }: TranslationEntry) =>
  `\n${JSON.stringify(key)}: {\nmessage: ${JSON.stringify(message)},\ndescription: ${JSON.stringify(description)},\n},`;

/**
 * A catalog file's text with `removed` entries cut out and `added` ones
 * inserted, every other byte untouched. Each new entry goes after the nearest
 * key before it in `order` (the locale's expected order), else first in the
 * default-exported object. Regenerating the file instead re-sorted and
 * reformatted whole catalogs, so adding one key showed up as hundreds of
 * changed lines (w0/m3). Format the result with Prettier.
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
    const slot = parseCatalog(text).entries.get(key);
    if (slot) text = text.slice(0, slot.start) + text.slice(slot.end);
  }
  for (const [index, key] of changes.order.entries()) {
    const entry = changes.added[key];
    if (!entry) continue;
    const { entries, firstSlot } = parseCatalog(text);
    let before: CatalogSlot | undefined;
    for (let i = index - 1; i >= 0 && !before; i--) {
      before = entries.get(changes.order[i]);
    }
    const at = before?.end ?? firstSlot;
    if (at === undefined) {
      throw new Error(`no catalog object to add ${key} to`);
    }
    const comma = before && !before.hasComma ? "," : "";
    text = text.slice(0, at) + comma + renderEntry(key, entry) + text.slice(at);
  }
  return text;
}
