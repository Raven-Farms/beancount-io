# w4 · m44 — Refuse CSV currency-symbol conflicts before importing

**Worker:** worker1 **Goal:** Smart Import cannot silently prepare euro/pound amounts in a different selected currency. **Status:** todo

**Severity:** major. **Estimate:** 190m across six tasks, dashboard only. The observed defect is incorrect prepared monetary units; no wrong-unit transaction was booked by QA.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Retain explicit currency evidence from bank amount tokens | 45m | — |
| [t002](./t002.md) | Refuse selected rows that conflict with the import currency | 55m | t001 |
| [t003](./t003.md) | Verify and explain the single-currency import workflow | 20m | t002 |
| [t004](./t004.md) | Simplify the bounded currency guard | 15m | t003 |
| [t005](./t005.md) | Prove parsing, configuration and prepared-unit agreement | 40m | t003 |
| [t006](./t006.md) | Verify the repaired journeys and archive the milestone | 15m | t004, t005 |

## Definition of done

- [ ] A selected amount carrying an unambiguous currency symbol cannot be submitted under a conflicting Currency choice. Explain the row/unit conflict accessibly and attempt0 BulkEntries while it remains.
- [ ] The reproduced euro/pound mixed file cannot be silently imported wholly as USD or EUR. The existing single-currency workflow tells the reader to choose matching rows or split the file; no automatic conversion or new multi-currency import feature is required.
- [ ] A euro-only file with Currency EUR retains exact normalized numbers and prepares only EUR postings. Plain numeric USD and supported ambiguous-symbol cases remain compatible; do not guess a unique currency from `$` or `¥`.
- [ ] Guard selected rows only. Excluding the conflicting row, choosing the matching currency or deliberately editing its source amount can resolve the conflict without losing mappings/selection. Back/Configure restores coherent evidence and choices.
- [ ] Preview edits and normalized display do not erase the evidence needed by validation. Preserve bank spellings, decimal-convention/precision rules, signs, civil dates, stable row IDs, invalid-row refusal and pending submission guards.
- [ ] All introduced messages are translated in15 locales. Meaningful parser/form/submission regressions expose the original unit substitution; desktop/narrow repeats and dashboard format:check, lint, test and build pass.
- [ ] Observable behavior and limits are recorded before /pm closes and archives this milestone. No actual AI operation or hosted import is needed to prove the guarded payload boundary.

## Source + Goal linkage

- **Source:** Continuous dashboard QA, 2026-10-21, five fresh real-UI/pre-transport controls. Full reproduction, source and dedupe are in [FINDINGS.md](./FINDINGS.md).
- **Goal linkage:** **A2 — Frictionless onboarding:** a newcomer can import a bank export without its explicit euro/pound units becoming dollars behind a valid preview.
- **Expected outcome:** the first import either prepares the amount in its matching selected unit or refuses with a concrete currency/row remedy before writing.
- **Why now:** bank-amount spelling support and exact decimal submission are shipped, but the currency evidence is stripped independently of the selected global unit. A post-write ledger check cannot recover a symbol omitted from the request. Parsing/edit lifetime, selected-row validation, localized guidance and integrated coverage exceed a sub-hour note. Adoption surface is included because this changes the import review/refusal flow.

## Scope and dedupe

Dashboard CSV parsing, Configure validation and the existing prepared transaction boundary only. [W0/007](../../w0/done/007.md) added accepted bank spellings; retain that support. [W3/421](../../w3/done/421.md), completed through CLI milestone49, owns the equivalent separate CLI currency resolution/refusal. [W3/640](../../w3/done/640.md) adds post-write ledger-error warnings, which cannot detect that a numerically valid USD request originally contained euros. Existing decimal normalization, draft and pending-edit repairs remain required. No cross-package import, backend/API/parity change, dependency, FX calculation, account-currency inference overhaul or per-row currency feature.
