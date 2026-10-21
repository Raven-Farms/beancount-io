# w4 · m40 — Keep picker popups sized and scrollable inside modals

**Worker:** worker1 **Goal:** Dates and account suggestions remain reachable by ordinary scrolling in short browser viewports and modal forms. **Status:** blocked (t001, t002 done; t003 and t005 need real-viewport browser checks)

**Severity:** minor. **Estimate:** 145m across six tasks, dashboard only.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Fit DatePicker content to available viewport height — **DONE** | 35m | — |
| [t002](./done/t002.md) | Restore nested-popup scrolling without unlocking the modal — **DONE** | 50m | t001 |
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

## Blocked

**Blocked 2026-10-20** — the repair shipped; t003 and t005 need real portal geometry and native wheel/pointer input in a browser, so t004 Simplify and t006 Closeout (which follow t003) wait too.

- **Shipped baseline:** `eeb14c2b2`. DatePicker's popup is capped at Radix's `--radix-popover-content-available-height` with an internal `overflow-y-auto overscroll-contain` region, so the header and every week stay reachable at short heights. The shared `PopoverContent` stops `wheel` and `touchmove` propagation at the popup element (a native, passive listener): the Dialog/Sheet scroll lock listens on `document` and was cancelling scrolling it did not start inside its own content, while the page behind stays locked. Clicks, keys, focus, the Combobox's nonmodal typing and its existing available-height list are untouched. `modal-popup-scroll.test.tsx` drives a real Dialog with DatePicker and a real Sheet with Combobox: a native wheel inside the popup is no longer cancelled, one on the page behind still is, the final date selects and typing keeps focus; it fails with the change reverted. Dashboard format, lint, test and build pass. jsdom has no layout, so viewport bounds and actual scroll positions are not proven here.
- **Blocker:** t003/t005 require real browser viewports (844×390, 568×320, 390×360, 390×844), native wheel and raw pointer clicks, which this worker cannot run — no browser is available.
- **Unblock:** after `eeb14c2b2` or later is deployed, QA repeats FINDINGS.md's Open Account DatePicker (August 2026 at 844×390 and 568×320, plus the 390×844 control) and the 390×360 Filter Sheet Account list: wheel moves the popup's scrollTop, a raw click on the final date/option selects it, the body stays locked, keyboard and resize-while-open still work, and the desktop inline picker and a standalone DatePicker are unchanged; then close t003/t005, run t004's /simplify and t006. **Who:** the user (deploy) and the dashboard QA loop.

