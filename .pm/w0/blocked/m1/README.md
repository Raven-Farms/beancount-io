# w0 · m1 — Translate the English copies shipped in non-English catalogs, and guard against them

**Worker:** worker1 **Goal:** a German, Russian, or Chinese user sees Receipt upload, Bank Connections, and Settings billing in their language, and CI fails the next time a whole message ships as an English copy **Status:** blocked (t001–t004 done)

## Tasks (in order)

| id   | title                                                          | est | depends_on       |
| ---- | -------------------------------------------------------------- | --- | ---------------- |
| t001 | Translate the Receipt catalog in its 11 untranslated locales   | 45m | —                | — **DONE**
| t002 | Translate the Plaid catalog in all 14 non-English locales       | 60m | —                | — **DONE**
| t003 | Translate the remaining residual keys across 14 feature catalogs | 45m | —                | — **DONE**
| t004 | Fail CI on whole-message English copies in non-English catalogs  | 45m | —                | — **DONE**
| t005 | Adoption surface                                                 | 20m | t001, t002, t003, t004 |
| t006 | Simplify                                                         | 15m | t005             |
| t007 | Test coverage                                                    | 30m | t005, t006       |
| t008 | Closeout                                                         | 10m | t007             |

Implementation totals about 195 minutes, and all eight tasks about 270. That's well past a sub-hour note.

## Blocked

**Blocked 2026-10-15** — t005 (Adoption surface) needs the definition of done's first check, which is live: `/receipt`, `/plaid-connections` and `/settings/general` rendered in de, ru and zh with no English chrome. The translations (`68bb3f58`, `de55789f`, `a821d9c1`) and the CI guard (`036a499b`) are on `main`, and `dashboard/AGENTS.md` now tells translators about the guard (shipped with this block). Production still serves an older bundle, and a local dev server can't render these authenticated routes against the hosted API, so the live check can't run yet. t006–t008 depend on t005 and wait with it.

**Unblock:** a production dashboard deploy that includes `036a499b`. Whoever runs beancount.io deploys can clear it. Then repeat the three-route check in de/ru/zh and continue with t005.

## Definition of done

- With the language set to German, Russian, and Chinese, `/ledger/<owner>/<ledger>/receipt` and `/plaid-connections` render no English sentences in the app chrome. The Settings billing card is translated too. Ledger data, brand names, and code identifiers stay as they are.
- The live inventory script below reports zero keys in every non-English catalog whose message is identical to English and contains two or more lowercase English words, apart from entries on a reviewed, commented allowlist.
- A test in `dashboard/src/test/` fails when a non-English message equals its English source, unless the key is allowlisted with a reason. It runs in `yarn test`.
- Dashboard format, lint, test, and build gates pass.

## Reproduction and evidence

Production `https://beancount.io`, 2026-10-15, local main `575a8798`. QA-owned headless Chromium, 1440×1000, authenticated QA owner on a synthetic ledger. Read-only. The language was switched by setting the app's own `i18nextLng` cookie/localStorage to `de` (as `persistLanguage` does), then restored to `en`.

The page text of 22 ledger routes was compared between `en` and `de`. Apart from ledger data and third-party library labels, two pages are still English under German:

- `/receipt`: "Upload Receipt", "Upload a receipt image or PDF to record a transaction in your ledger", "Drag and drop your receipt here", "Choose File".
- `/plaid-connections`: "Back to Transactions", "Bank Connections", "Manage account mappings, sync, and disconnect banks."

Source inventory from `dashboard/src`: messages in a non-English `locales/*.ts` that are byte-identical to `en.ts` and contain at least two lowercase English words. This is a lower bound, because title-case copies like "Upload Receipt" are not counted.

| catalog | keys | locale×key strings |
| --- | --- | --- |
| `features/plaid/locales` | 34 | 296 |
| `features/receipt/locales` | 19 | 209 |
| `features/user-settings/locales` | 9 | 31 |
| `features/ai-agent/locales` | 2 | 28 |
| `features/ledger-data/settings/general-settings-section/locales` | 3 | 21 |
| `features/user-profile/locales` | 1 | 12 |
| ten more ledger-data / bql / editor / dashboard catalogs | 1–4 each | 22 |
| **total** | | **619** |

## Root cause

The catalogs were filled with English copies instead of `[TODO]` markers, so `yarn i18n:prepare` (w4/158) reports them as done. `dashboard/src/test/locale-stray-english.test.ts` and `locale-scan.ts` look only for English words *stranded inside* a translated message: `untranslatedEnglishTail` returns `[]` when `message === english` (`locale-scan.ts` ~342), and `strayEnglishWords` targets mixed-script messages. `translations.test.ts` checks key shape only. An entirely English message therefore passes every guard.

## Source + Goal linkage

- **Source:** continuous dashboard QA (`/qa-find-bugs-dashboard`, 2026-10-15), German locale sweep plus source inventory.
- **Goal linkage:** **A2 — Frictionless onboarding.** Receipt capture and bank connection are first-week flows. A newcomer using one of the 14 non-English languages hits English exactly where they start importing data.
- **Expected outcome:** non-English users can upload a receipt and manage bank connections in their language, and copy-pasted English can't come back without a red CI run.
- **Why now:** earlier repairs (w4/155 OAuth, w4/149 and w4/153 Russian, w4/156 four locales) each fixed one slice by hand after an accidental discovery. The guard gap is why it keeps recurring.
- **Adoption surface:** included, because these are visible dashboard journeys in every supported language.
