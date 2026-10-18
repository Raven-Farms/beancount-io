import { PLURAL_SUFFIX, pluralCategories } from "../../src/i18n/plural";

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
    entries[key] = { message: `[TODO] ${message}`, description };
    added.push(key);
  }
  const removed = Object.keys(target).filter((key) => !expected.has(key));
  return { entries, added, removed };
}
