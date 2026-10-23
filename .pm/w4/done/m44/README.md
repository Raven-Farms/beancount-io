# w4 · m44 — Refuse CSV currency-symbol conflicts before importing

**Worker:** worker1 **Goal:** Smart Import cannot silently prepare euro/pound amounts in a different selected currency. **Status:** done

**Severity:** major. **Estimate:** 190m across six tasks, dashboard only. The observed defect is incorrect prepared monetary units; no wrong-unit transaction was booked by QA.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Retain explicit currency evidence from bank amount tokens — **DONE** | 45m | — |
| [t002](./done/t002.md) | Refuse selected rows that conflict with the import currency — **DONE** | 55m | t001 |
| [t003](./done/t003.md) | Verify and explain the single-currency import workflow — **DONE** | 20m | t002 |
| [t004](./done/t004.md) | Simplify the bounded currency guard — **DONE** | 15m | t003 |
| [t005](./done/t005.md) | Prove parsing, configuration and prepared-unit agreement — **DONE** | 40m | t003 |
| [t006](./done/t006.md) | Verify the repaired journeys and archive the milestone — **DONE** | 15m | t004, t005 |

## Definition of done

- [x] A selected amount carrying an unambiguous currency symbol cannot be submitted under a conflicting Currency choice. Explain the row/unit conflict accessibly and attempt0 BulkEntries while it remains.
- [x] The reproduced euro/pound mixed file cannot be silently imported wholly as USD or EUR. The existing single-currency workflow tells the reader to choose matching rows or split the file; no automatic conversion or new multi-currency import feature is required.
- [x] A euro-only file with Currency EUR retains exact normalized numbers and prepares only EUR postings. Plain numeric USD and supported ambiguous-symbol cases remain compatible; do not guess a unique currency from `$` or `¥`.
- [x] Guard selected rows only. Excluding the conflicting row, choosing the matching currency or deliberately editing its source amount can resolve the conflict without losing mappings/selection. Back/Configure restores coherent evidence and choices.
- [x] Preview edits and normalized display do not erase the evidence needed by validation. Preserve bank spellings, decimal-convention/precision rules, signs, civil dates, stable row IDs, invalid-row refusal and pending submission guards.
- [x] All introduced messages are translated in15 locales. Meaningful parser/form/submission regressions expose the original unit substitution; desktop/narrow repeats and dashboard format:check, lint, test and build pass.
- [x] Observable behavior and limits are recorded before /pm closes and archives this milestone. No actual AI operation or hosted import is needed to prove the guarded payload boundary.

## Source + Goal linkage

- **Source:** Continuous dashboard QA, 2026-10-21, five fresh real-UI/pre-transport controls. Full reproduction, source and dedupe are in [FINDINGS.md](./FINDINGS.md).
- **Goal linkage:** **A2 — Frictionless onboarding:** a newcomer can import a bank export without its explicit euro/pound units becoming dollars behind a valid preview.
- **Expected outcome:** the first import either prepares the amount in its matching selected unit or refuses with a concrete currency/row remedy before writing.
- **Why now:** bank-amount spelling support and exact decimal submission are shipped, but the currency evidence is stripped independently of the selected global unit. A post-write ledger check cannot recover a symbol omitted from the request. Parsing/edit lifetime, selected-row validation, localized guidance and integrated coverage exceed a sub-hour note. Adoption surface is included because this changes the import review/refusal flow.

## Scope and dedupe

Dashboard CSV parsing, Configure validation and the existing prepared transaction boundary only. [W0/007](../../../w0/done/007.md) added accepted bank spellings; retain that support. [W3/421](../../../w3/done/421.md), completed through CLI milestone49, owns the equivalent separate CLI currency resolution/refusal. [W3/640](../../../w3/done/640.md) adds post-write ledger-error warnings, which cannot detect that a numerically valid USD request originally contained euros. Existing decimal normalization, draft and pending-edit repairs remain required. No cross-package import, backend/API/parity change, dependency, FX calculation, account-currency inference overhaul or per-row currency feature.

## Closeout (2026-10-22)

- **Implementation:**
  - The dashboard reads each amount cell's currency symbol with the CLI's table (w3/421) and keeps the parser's numeric normalization unchanged.
  - Configure refuses selected rows whose symbol rules out the chosen Currency. A live alert names the rows, symbol, possible currencies and chosen currency, with the single-currency remedy. Import sends nothing and moves focus to that alert until the reader chooses the matching currency, deselects the rows, or edits the amount.
  - `$`, `¥` and bare numbers never conflict.
  - The messages are translated in 15 locales, and the importer's `AGENTS.md` records the rule.
- **Evidence:** a local production build at 1440 and 390 px against replayed public reads, with every write held in the browser.
  - The €/£ file sends 0 BulkEntries under USD and under EUR.
  - With the £ row deselected, it prepares exactly `-1.25 EUR` / `+1.25 EUR`.
  - Euro-only under EUR and bare numbers under USD prepare their exact amounts.
  - Back → Continue keeps the conflict.
  - Both refusal regressions fail against the original form ([t005](./done/t005.md)).
- **Gates:** dashboard `yarn format:check`, `yarn lint`, `yarn test` (641 files, 6697 tests) and `yarn build` pass, and so does `scripts/check-agent-guidance.py`. No backend, API or cross-package change.
- **Target and limits:**
  - Verified locally, not on the deployed site. QA should repeat FINDINGS.md's production steps after deployment.
  - AI-parsed rows carry no symbol evidence, because the backend returns bare numbers; closing that would need an API change.
  - A cell carrying two different symbols is judged by its first, as the CLI does.
  - The synthetic fixture recorded reads only, and no hosted import, AI call or write was made.
