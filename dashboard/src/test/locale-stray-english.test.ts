import { describe, expect, it } from "vitest";
import * as locales from "@/i18n/locales";
import {
  EN_COMPARED_LOCALES,
  SCANNED_LOCALES,
  UNCLASSIFIED_LOCALES,
  type ScannedLocale,
  strayEnglishWords,
  untranslatedEnglishTail,
  untranslatedWholeMessage,
} from "./locale-scan";
import en from "@/i18n/locales/en";

/**
 * A translation pass that replaces a leading token and leaves the rest in
 * English has now been repaired three times — Catalan (w4/m14), Russian
 * (w4/149) and Ukrainian (w4/m24). Each was found by accident while chasing
 * something else. This guard looks for it in every locale whose script is not
 * Latin, so a fourth cannot ship unnoticed.
 */

const ALL = locales as unknown as Record<string, Record<string, string>>;

/**
 * Damage that exists on `main` today, listed key by key so that repairing one
 * forces this list to shrink. Each group names the note that owns the work;
 * nothing is hidden in the allowlist, which is only for Latin that belongs in
 * a translated string.
 */
const KNOWN_DEVIATIONS: Partial<
  Record<ScannedLocale, { note: string; keys: readonly string[] }>
> = {
  // Empty, and that is the point: every scanned locale is clean as of
  // w4/153 (Russian), w4/155 (the OAuth keys) and w4/156 (Bulgarian,
  // Persian, Korean and Chinese). The shape stays so that a locale which
  // cannot be repaired immediately is recorded key by key against the note
  // that owns it, rather than hidden in the allowlist.
};

const isKnown = (locale: ScannedLocale, key: string) =>
  KNOWN_DEVIATIONS[locale]?.keys.includes(key) ?? false;

const SCANNED = Object.keys(SCANNED_LOCALES) as ScannedLocale[];

describe("no locale ships a half-translated message", () => {
  it.each(SCANNED)(
    "%s leaves no English word stranded in its own script",
    (locale) => {
      const offenders: string[] = [];
      for (const [key, message] of Object.entries(ALL[locale] ?? {})) {
        if (isKnown(locale, key)) continue;
        const stray = strayEnglishWords(message, locale);
        if (stray.length) {
          offenders.push(`${locale}/${key}: ${message} -> ${stray.join(", ")}`);
        }
      }
      expect(offenders).toEqual([]);
    },
  );

  it("keeps every known deviation real, so the list shrinks as they are fixed", () => {
    // A key listed here that is already clean would quietly excuse a future
    // regression on that key.
    const stale: string[] = [];
    for (const [locale, { note, keys }] of Object.entries(KNOWN_DEVIATIONS) as [
      ScannedLocale,
      { note: string; keys: readonly string[] },
    ][]) {
      for (const key of keys) {
        const message = ALL[locale]?.[key];
        if (message === undefined) {
          stale.push(`${note} ${locale}/${key}: key no longer exists`);
          continue;
        }
        const damaged = strayEnglishWords(message, locale).length > 0;
        if (!damaged) stale.push(`${note} ${locale}/${key}: already clean`);
      }
    }
    expect(stale).toEqual([]);
  });

  it.each(EN_COMPARED_LOCALES)(
    "%s leaves no English tail against the same key in en",
    (locale) => {
      // Reaches the Latin-script locales, where script proves nothing: `Cuenta
      // Balance` and `Excluir Ledger` are only visible beside their English
      // source.
      const offenders: string[] = [];
      for (const [key, message] of Object.entries(ALL[locale] ?? {})) {
        const english = en[key];
        if (english === undefined) continue;
        const tail = untranslatedEnglishTail(message, english, locale);
        if (tail.length) {
          offenders.push(`${locale}/${key}: ${message} -> ${tail.join(" ")}`);
        }
      }
      expect(offenders).toEqual([]);
    },
  );

  it("classifies every supported language as scannable or Latin-script", () => {
    // A new non-Latin locale added to SUPPORTED_LANGUAGES would otherwise go
    // unscanned with nothing failing.
    expect(UNCLASSIFIED_LOCALES).toEqual([]);
  });

  it("withholds an allowlisted term's exemption when it is glued to the script", () => {
    // The exemption exists for terms standing as their own word. `Банк` and
    // `Bank` side by side is the defect, and stripping `Bank` first would hide
    // it — the reason the rule is inside the predicate rather than a second
    // pass over the same catalogs.
    expect(strayEnglishWords("Банк Bank", "uk")).toEqual([]);
    // The Latin run is what is reported; the Cyrillic prefix is what makes it
    // damage rather than an exempt term.
    expect(strayEnglishWords("БанкBank", "uk")).toEqual(["Bank"]);
    // Japanese writes brand names against its script with no space, so there
    // the exemption still holds.
    expect(strayEnglishWords("Beancountについて", "ja")).toEqual([]);
  });

  it.each(SCANNED)(
    "carries no deviation for %s — every scanned locale is clean",
    (locale) => {
      expect(KNOWN_DEVIATIONS[locale]).toBeUndefined();
    },
  );
});

/**
 * The shared-tail check above deliberately ignores a message that is entirely
 * English, because a one-word label such as `Status` is often correct in
 * another language too. Table column headers are where that gap bit: German
 * Events shipped `Datum`, `Type`, `Description` (w4/169). So German headers
 * are compared whole, against a short list of words German UIs really do use.
 */
type StructuredCatalog = Record<
  string,
  { message: string; description?: string }
>;

const FEATURE_CATALOGS = import.meta.glob<{ default: StructuredCatalog }>(
  "/src/**/locales/{en,de}.ts",
  { eager: true },
);

/** English headers German keeps: loanwords and the journal's literal flag. */
const GERMAN_SHARED_HEADERS = new Set(["F", "Status", "Links", "Meta", "Tags"]);

describe("German table column headers", () => {
  it("are translated unless German uses the same word", () => {
    const untranslated: string[] = [];
    for (const [path, catalog] of Object.entries(FEATURE_CATALOGS)) {
      if (!path.endsWith("/en.ts")) continue;
      const german =
        FEATURE_CATALOGS[path.replace(/en\.ts$/, "de.ts")]?.default;
      for (const [key, { message, description }] of Object.entries(
        catalog.default,
      )) {
        if (!/column header/i.test(description ?? "")) continue;
        if (GERMAN_SHARED_HEADERS.has(message)) continue;
        if (german?.[key]?.message === message) {
          untranslated.push(`${path} ${key}: ${message}`);
        }
      }
    }
    expect(untranslated).toEqual([]);
  });
});

/**
 * Messages a locale deliberately keeps identical to English, keyed
 * `locale/key`, each with the reason it is correct there. The list exists so
 * the check below can stay strict; an entry that stops being identical fails
 * the stale-entry test rather than lingering as a silent excuse.
 */
const IDENTICAL_BY_DESIGN: Record<string, string> = {
  "bg/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "ca/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "de/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "es/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "fa/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "fr/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "ja/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "ko/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "nl/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "pt/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "ru/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "sk/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "uk/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "zh/userProfile.openLedgerName":
    "Open Ledger is the proper name of the public collection account",
  "bg/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "ca/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "de/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "es/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "fa/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "fr/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "nl/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "pt/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "ru/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "sk/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "uk/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "zh/page.accounts.accountSubAccountPlaceholder":
    "Placeholder written in Beancount account-path syntax",
  "de/seo.ledgerPullRequest.title":
    "These catalogs keep the Git term Pull Request throughout",
  "nl/seo.ledgerPullRequest.title":
    "These catalogs keep the Git term Pull Request throughout",
};

describe("no locale ships an English message copied whole", () => {
  it.each(EN_COMPARED_LOCALES)(
    "%s translates every copied message",
    (locale) => {
      const offenders: string[] = [];
      for (const [key, message] of Object.entries(ALL[locale] ?? {})) {
        const english = en[key];
        if (english === undefined) continue;
        if (IDENTICAL_BY_DESIGN[`${locale}/${key}`]) continue;
        if (untranslatedWholeMessage(message, english).length) {
          offenders.push(`${locale}/${key}: ${message}`);
        }
      }
      expect(offenders).toEqual([]);
    },
  );

  it("keeps every identical-by-design entry identical", () => {
    const stale = Object.keys(IDENTICAL_BY_DESIGN).filter((entry) => {
      const [locale, ...rest] = entry.split("/");
      const key = rest.join("/");
      return ALL[locale]?.[key] !== en[key];
    });
    expect(stale).toEqual([]);
  });

  it("flags a whole English copy but not brand or notation alone", () => {
    expect(
      untranslatedWholeMessage("Upload Receipt", "Upload Receipt"),
    ).toEqual(["Upload", "Receipt"]);
    expect(
      untranslatedWholeMessage(
        "{count} bank(s) need reconnecting",
        "{count} bank(s) need reconnecting",
      ),
    ).toEqual(["bank", "need", "reconnecting"]);
    // Identical in many languages: brand, format and status tokens.
    expect(untranslatedWholeMessage("Plaid", "Plaid")).toEqual([]);
    expect(untranslatedWholeMessage("CSV · PDF", "CSV · PDF")).toEqual([]);
    expect(untranslatedWholeMessage("Status", "Status")).toEqual([]);
    // A translated message is not a copy, whatever its words.
    expect(
      untranslatedWholeMessage("Beleg hochladen", "Upload Receipt"),
    ).toEqual([]);
  });
});
