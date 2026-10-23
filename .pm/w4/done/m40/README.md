# w4 · m40 — Keep picker popups sized and scrollable inside modals

**Worker:** worker1 **Goal:** Dates and account suggestions remain reachable by ordinary scrolling in short browser viewports and modal forms. **Status:** done

**Severity:** minor. **Estimate:** 145m across six tasks, dashboard only.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Fit DatePicker content to available viewport height — **DONE** | 35m | — |
| [t002](./done/t002.md) | Restore nested-popup scrolling without unlocking the modal — **DONE** | 50m | t001 |
| [t003](./done/t003.md) | Verify picker adoption surfaces and interaction contracts — **DONE** | 10m | t002 |
| [t004](./done/t004.md) | Simplify the bounded popup integration — **DONE** | 10m | t003 |
| [t005](./done/t005.md) | Prove actual scroll, reachability and background locking — **DONE** | 35m | t003 |
| [t006](./done/t006.md) | Close out and archive the milestone — **DONE** | 5m | t004, t005 |

## Definition of done

- [x] DatePicker fits available height at844×390 and568×320, with Today/month/year and all six-week calendar rows reachable. Normal390×844 layout remains correct.
- [x] Native wheel scrolling works in a DatePicker inside Open Account and an Account Combobox inside the390×360 Filter Sheet; the last option/date can be selected by an ordinary visible pointer click.
- [x] Keyboard focus/scroll/selection and resizing while open work. Background modal/page scrolling stays locked; desktop inline Combobox scrolling and standalone DatePicker behavior remain intact.
- [x] Preserve nonmodal input focus/typing, caller event ownership, dismissal/focus return, civil-date/draft semantics, RTL and existing height caps. No blanket document-level event override, dependency or API change.
- [x] Meaningful real portal/viewport/native-input verification plus dashboard format/lint/test/build pass. Record deployment/build limits before closeout.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. [Findings](./FINDINGS.md) preserve W4/293's calendar proof and the independent shared Combobox wheel follow-up. **A2 — Frictionless onboarding:** readers must be able to choose a date or account through the provided controls at short window heights. DatePicker sizing and shared modal-popup wheel integration are two bounded implementation units; combined regression coverage exceeds an hour. Adoption verification is included because these are customer-facing controls used across financial workflows.

## Scope

Common DatePicker popup sizing and an appropriate shared/consumer integration for portaled scrolling inside Dialog/Sheet. DatePicker has seven feature callers; Combobox serves shared ledger filters and account/currency/source-file/payee/narration/operating-currency wrappers. Live failures are Accounts Open Date and the shared Filter Sheet's Account list; other callers are compatibility scope. Keep the existing Combobox viewport-height fix from w3/169 and coordinate the independent IME fixes W4/286/288/292 without conflating their event semantics. This milestone makes no ledger writes, backend/parity changes or native-mobile changes.

## Deployment verification

**Unblocked 2026-10-22** — the repaired DatePicker and shared Popover are deployed, and isolated headless Chromium 155 passed the original viewport, native-wheel and visible-pointer repros plus resize, keyboard, modal locking and compatibility controls; detailed results and the previous blocker are preserved in [FINDINGS.md](./FINDINGS.md). t003 is complete; t004, t005's remaining regression/gate review and t006 remain open.

## Closeout (2026-10-22)

- **Implementation:** `eeb14c2b2` caps the DatePicker popup at Radix's measured available height with an internal scroll region, and makes the shared `PopoverContent` keep wheel and touch scrolling inside portaled popups that a Dialog or Sheet scroll lock would cancel. The simplify pass (t004) now composes the caller's `onWheel`/`onTouchMove` instead of hand-merging refs for native listeners. No document-level override, dependency or API change.
- **Evidence:**
  - QA's deployed checks passed at 844×390, 568×320, 390×360 and 390×844: native wheel, raw pointer selection, keyboard, resize while open, the modal lock, focus return, and the standalone and desktop controls ([FINDINGS.md](./FINDINGS.md)).
  - The simplified handlers reproduce the same scroll figures on a local production build.
  - Both regressions fail with the repair reverted ([t005](./done/t005.md)).
- **Gates:** dashboard `yarn format:check`, `yarn lint`, `yarn test` (641 files, 6697 tests) and `yarn build` pass.
- **Limits:**
  - The simplified handlers are verified locally; QA's post-deploy repeat is still owed.
  - Native touch, physical screen readers, other engines and RTL rendering are unverified.
  - A shared default height cap for other popovers was left as an unverified possible follow-up.
