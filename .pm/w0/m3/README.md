# w0 · m3 — Make i18n:prepare safe to run and honest about English copies

**Worker:** worker1 **Goal:** running the dashboard's translation tool on a synced tree changes nothing, keeps every locale's CLDR plural forms, reports whole English copies as untranslated, and CI fails when catalogs drift **Status:** todo (t001–t002 done)

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | Plural-aware key sync via `Intl.PluralRules` | 45m | — | — **DONE**
| t002 | Write nothing on an already-synced tree | 30m | t001 | — **DONE**
| t003 | `--check` mode that fails on drift or `[TODO]`, wired into dashboard CI | 30m | t002 |
| t004 | Report whole English copies as untranslated | 30m | — |
| t005 | Adoption surface | 20m | t003, t004 |
| t006 | Simplify | 15m | t005 |
| t007 | Test coverage | 30m | t005, t006 |
| t008 | Closeout | 10m | t007 |

## Definition of done

- `yarn i18n:prepare` on `main` changes no file.
- Russian, Ukrainian and Slovak keep their `_few` / `_many` plural keys; Chinese, Japanese and Korean gain no `_one` key.
- `i18n:prepare --check` passes on `main` and exits non-zero on fixtures with a missing key, an obsolete key, a deleted Russian plural form, or a `[TODO]` marker; dashboard CI runs it.
- The report lists whole English copies (outside the reasoned `IDENTICAL_BY_DESIGN` allowlist) as not completed.
- Dashboard format, lint, test and build pass.

## Source + Goal linkage

- **Source:** `/pm-brainstorm` for w0 (2026-10-17) and the follow-ups recorded when w0/m1 closed (`done/m1/done/t006.md`, `t008.md`). Running `scripts/prepare-translations.ts` on `main` (2026-10-17) rewrote 88 catalog files: it removed 68 plural keys each from Russian, Ukrainian and Slovak, removed obsolete-looking `_many` keys from Catalan, Spanish, French and Portuguese, and added 34 `[TODO] …_one` keys to Chinese — because `syncTranslations` compares key sets against `en.ts` without knowing that plural suffixes differ per locale. Its completion count also treats a message copied whole from English as done (the root cause w0/m1 named). Prior tooling work: w4/158 (edit-time half-translation detection) and w4/159 (no auto-generated English into shared catalogs) — neither covers plurals or a check mode.
- **Goal linkage:** **A2 — Frictionless onboarding** and **A3 — Community & distribution.** Non-English users keep correct plurals, and translators and contributors can run the documented tool without corrupting catalogs.
- **Expected outcome:** a contributor can run `yarn i18n:prepare` safely; catalog drift and copied English fail CI instead of reaching users in 14 languages.
- **Why now:** w0/m1 just made whole English copies fail CI; the tool translators use still reports them as done and, run today, would delete real Russian plural forms.
- **Adoption surface:** included. The translator workflow in `dashboard/AGENTS.md` (Internationalization) and the script's printed report change.
