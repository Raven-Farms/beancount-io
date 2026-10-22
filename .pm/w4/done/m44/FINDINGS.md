# Accepted currency symbols disappear before every row receives the global currency

Production https://beancount.io, 2026-10-21, local main0eb3b6ffa; QA-owned headless isolated Chromium155.0.8059.85, English/light, authenticated owner of the designated disposable synthetic ledger. Fresh1440×1000 and390×844 contexts. UI, CSV parsing and ordinary reads are unmodified. Each actual BulkEntries request is captured and aborted before transport:0 hosted writes, AI calls or hosted fixtures.

## Reproduce

Upload this local CSV and continue to Configure:

```csv
Date,Payee,Description,Amount
2026-10-21,qa-20261021-token-1,qa currency token,€-1.25
2026-10-22,qa-20261021-token-2,qa currency token,£2.50
```

1. Preview says **2 Valid**. The amount buttons display normalized **-1.25** and **2.50**, with no currency in their visible/current-value labels.
2. Configure defaults Currency to the ledger's USD. Set source Assets:Cash and both targets Expenses:Food. Both rows are selected; target warnings disappear. No currency conflict message appears. The amount column shows-1.25/2.5.
3. Activate **Import 2 Transactions**. Its genuine prepared request contains TRANSACTION entries dated2026-10-21/22. The first source/counter postings are **-1.25 USD / +1.25 USD**; the second are **+2.50 USD / -2.50 USD**. Both explicit source symbols have disappeared. The guard then aborts the request and the normal Import Failed/Start Over state appears. This proves preparation, not server acceptance or persistence.
4. A fresh narrow context independently repeats exactly those USD units and no conflict warning.
5. In a third fresh narrow context, explicitly choose EUR for the same mixed file. Both entries now prepare EUR postings, including the pound row. One global currency cannot honor both accepted rows without excluding/splitting them; merely changing the default does not resolve the mixed-file case.

Passing serialization controls: a fresh narrow euro-only file (€-1.25/€2.50) with Currency EUR prepares exactly-1.25/+2.50 EUR and balanced opposite postings. A fresh desktop plain-number file (-1.25/2.50) retains default USD and prepares those exact USD numbers. These are unit/decimal controls; their requests were also preblocked, so no account-constraint or successful booking claim is made.

Expected: retain explicit source-unit evidence and refuse a selected row's contradiction before sending BulkEntries. Currency symbols are not FX instructions: replacing the unit while retaining the number performs no conversion. Keep supported bank-formatted numbers; do not repair this by rejecting every symbol, guessing ambiguous dollar/yen units or sending the CSV to AI.

## Cause

- `dashboard/src/features/importer/utils/csv-validator.ts:133–185` recognizes and removes Unicode currency symbols while splitting an amount's sign/core. parseAmount returns the exact numeric decimal, with no semantic currency result.
- `lib/import-config-draft.ts:54–95` retains amountInput and amountDecimal for valid rows. The original token is still available to the form, so a bounded guard is possible without an API change.
- `components/steps/configure/transaction-config-form.tsx:65–104` validates a nonempty global currency and row selection/targets, but never compares it with source symbols. At:173–193 it maps every selected row to currency:data.defaultCurrency and drops the original amountInput.
- `hooks/use-import-submit.ts:66–105` faithfully builds two postings from that supplied currency/normalized decimal. The server receives no original symbol to distinguish euro data from ordinary USD data. Correct balancing or a clean ledger check would not prove the chosen monetary unit matches the CSV.
- `common/providers/ledger-provider/ledger-provider.tsx:17` supplies the first operating currency, or USD, as primaryCurrency; the form defaults from it. This is a legitimate default for bare numbers, not evidence that an explicit euro token means USD.

Use a local, explicit source-unit policy consistent with the existing CLI refusal contract for unambiguous symbols. Preserve raw-token edits and the parser's numeric normalizations; compare the selected rows' evidence with the current form Currency before submission. Explain conflicts in the existing single-currency flow and let excluding rows/correcting the currency or source resolve them. No automatic FX, new per-row currency field, backend validation adapter, cross-package import or dependency is needed.

## Dedupe and deployment

Searched all board states for Smart Import currency/symbol handling, csv-validator symbol removal, contradictions and the actual consumer paths; reviewed open W4 milestones and targeted history. W0/007 shipped eb8bcd5f6's spelling support, W3/644 shipped8036f4349's decimal-convention display repair, and W3/564 shipped6ca64801b's normalized decimal submission. All are present and must remain. W3/421 is CLI-only and resolved in W3/m49; this is an independently reproduced dashboard consumer. W3/640's after-write error warning and W4/280's pending freeze do not compare source units. No current guard or already-shipped repair was found.

Credential-free public `/lgassets/ledger._ledgerOwner._ledgerName.import-gd5Uo27g.js.map` matches all four current implicated sources exactly:

| source | SHA-256 |
| --- | --- |
| csv-validator.ts | 75e871948fccc1d596c478be2439c075c5693f019f2e04651934672f640125ec |
| import-config-draft.ts | 4a717d30f0dcefa4e144f9320b2d719d8e9b9e3ebf5a63d5081b76596b023048 |
| transaction-config-form.tsx | 11d05a2ded65c474cf7bc91ea5840318f23a9c6cb7b0bef1c8cf80abdbb140f3 |
| use-import-submit.ts | e8efb440c5d1419f94c586bec0de1927c62e0ae3bc242b6199c361d2550b41b7 |

The searched production path is CSV parser → preview/edit rebuild → configuration draft/form → submit hook. Non-CSV/AI-produced rows and other clients are compatibility scope, not live evidence.

## Evidence and cleanup

Ignored dashboard/tmp/qa-20261020/dashboard-loop/currency-token-complete-controls.json retains all five fresh cases, raw tokens, Preview/configuration states, exact prepared posting numbers/units and source/cleanup metadata. currency-token-390-default-mixed.png and currency-token-390-EUR-eur.png crop the actual configuration form and were visually inspected. The same directory has mixed/EUR and plain/USD control captures. Public reproduction text above is sufficient without those local artifacts.

Each case has one blocked mutation,0 route errors and0 page exceptions. All child contexts close, leaving the original isolated QA session. No request/response fixture or AI parser is used, and no ledger content is changed. Actual wrong-unit booking, real server acceptance of the controls, unselected-row recovery, other locales/engines, speech and repaired behavior remain unverified. Report only; no product fix or test change.
