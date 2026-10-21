# w4 · m40 — Keep picker popups sized and scrollable inside modals

**Worker:** worker1 **Goal:** Dates and account suggestions remain reachable by ordinary scrolling in short browser viewports and modal forms. **Status:** todo

**Severity:** minor. **Estimate:** 145m across six tasks, dashboard only.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Fit DatePicker content to available viewport height | 35m | — |
| [t002](./t002.md) | Restore nested-popup scrolling without unlocking the modal | 50m | t001 |
| [t003](./t003.md) | Verify picker adoption surfaces and interaction contracts | 10m | t002 |
| [t004](./t004.md) | Simplify the bounded popup integration | 10m | t003 |
| [t005](./t005.md) | Prove actual scroll, reachability and background locking | 35m | t003 |
| [t006](./t006.md) | Close out and archive the milestone | 5m | t004, t005 |

## Definition of done

- [ ] DatePicker fits available height at844×390 and568×320, with Today/month/year and all six-week calendar rows reachable. Normal390×844 layout remains correct.
- [ ] Native wheel scrolling works in a DatePicker inside Open Account and an Account Combobox inside the390×360 Filter Sheet; the last option/date can be selected by an ordinary visible pointer click.
- [ ] Keyboard focus/scroll/selection and resizing while open work. Background modal/page scrolling stays locked; desktop inline Combobox scrolling and standalone DatePicker behavior remain intact.
- [ ] Preserve nonmodal input focus/typing, caller event ownership, dismissal/focus return, civil-date/draft semantics, RTL and existing height caps. No blanket document-level event override, dependency or API change.
- [ ] Meaningful real portal/viewport/native-input verification plus dashboard format/lint/test/build pass. Record deployment/build limits before closeout.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. [Findings](./FINDINGS.md) preserve W4/293's calendar proof and the independent shared Combobox wheel follow-up. **A2 — Frictionless onboarding:** readers must be able to choose a date or account through the provided controls at short window heights. DatePicker sizing and shared modal-popup wheel integration are two bounded implementation units; combined regression coverage exceeds an hour. Adoption verification is included because these are customer-facing controls used across financial workflows.

## Scope

Common DatePicker popup sizing and an appropriate shared/consumer integration for portaled scrolling inside Dialog/Sheet. DatePicker has seven feature callers; Combobox serves shared ledger filters and account/currency/source-file/payee/narration/operating-currency wrappers. Live failures are Accounts Open Date and the shared Filter Sheet's Account list; other callers are compatibility scope. Keep the existing Combobox viewport-height fix from w3/169 and coordinate the independent IME fixes W4/286/288/292 without conflating their event semantics. This milestone makes no ledger writes, backend/parity changes or native-mobile changes.
