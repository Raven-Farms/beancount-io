# w4 · m43 — Keep contrast selections visible and readable

**Worker:** worker1 **Goal:** Readers can see the selected state and read active choices before applying them in a contrast theme. **Status:** done

**Severity:** minor. **Estimate:** 340m across eleven tasks, dashboard only.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Preserve readable active labels across the four styling targets — **DONE** | 45m | — |
| [t006](./done/t006.md) | Keep the selected calendar day visible apart from focus — **DONE** | 25m | t001 |
| [t007](./done/t007.md) | Keep the Billing cycle visibly selected in forced colors — **DONE** | 20m | t001 |
| [t008](./done/t008.md) | Keep the Net Worth view visibly selected in forced colors — **DONE** | 20m | t001 |
| [t009](./done/t009.md) | Keep Budget filters visibly selected in forced colors — **DONE** | 20m | t001 |
| [t010](./done/t010.md) | Keep the Accounts type visibly selected in forced colors — **DONE** | 20m | t001 |
| [t011](./done/t011.md) | Keep ledger creation radio choices visibly selected in forced colors — **DONE** | 30m | t001 |
| [t002](./done/t002.md) | Verify the contrast behavior on its adoption surfaces — **DONE** | 65m | t006, t007, t008, t009, t010, t011 |
| [t003](./done/t003.md) | Simplify the bounded contrast repair — **DONE** | 10m | t002 |
| [t004](./done/t004.md) | Prove actual label and selected-state paint — **DONE** | 75m | t002 |
| [t005](./done/t005.md) | Close out and archive the milestone — **DONE** | 10m | t003, t004 |

## Definition of done

- [x] Under real browser forced-colors emulation, the active cue and actual label remain readable for CommandItem, shared Combobox options, pressed JournalFilters and default pill Tabs. Check light/dark at desktop/narrow widths on applicable real consumers, after transitions settle and while keyboard selection moves.
- [x] The committed single calendar day remains visibly selected when focus is on Today/month controls or a different tentative day. Native focus and selected state remain separately identifiable, with readable date numerals in both palettes.
- [x] Billing's Monthly/Yearly cycle remains visibly selected after focus leaves the group in forced light/dark at both widths. Keep both labels readable, a separate focus cue, correct aria-pressed and price/disclosure updates; cycle selection dispatches no checkout/subscription mutation.
- [x] Net Worth's Chart/Table mode stays visibly selected away from focus in both forced palettes and widths. Preserve its pressed semantics, native focus, actual renderer, URL view, period/ledger context and named table scroll region.
- [x] Both Budget filter groups and the Accounts type filter visibly distinguish the selected choice after focus leaves in both forced palettes and widths. Preserve readable labels, exactly-one pressed state per group, wrapping/overflow, native focus, real filtered results, Accounts URL/reload state and ordinary themes.
- [x] Ledger creation's start-kind and preset radio cards visibly distinguish the checked choice away from focus in both forced palettes and widths. Preserve readable labels/icons, native group/checked semantics, separate keyboard focus, stable card geometry and ordinary themes; no creation action is necessary.
- [x] Preserve the user's system palette, inactive labels, ordinary themes, dimensions, separate focus cues, pointer behavior and selection models. Any local adjustment exception must keep explicit system foreground/background values effective, including dark/theme overrides and descendant labels; no page-wide forced-color opt-out.
- [x] Account and ledger targets, report year, Journal filters and directive tabs still apply the same values. Preserve input focus/active descendants, native dialog return focus, retained account period and intentional cross-ledger filter clearing. No hosted write is necessary.
- [x] Preserve readable dark pill tabs, native Select options, underline profile tabs, shared Button focus, Switch and custom-row repairs. Audit callers and distinguish tested aliases from compatibility scope.
- [x] Meaningful paint/selection regressions expose the current unreadable text. Existing class/CSS checks are not the only visibility evidence. Dashboard format/lint/test/build pass; record actual browser evidence and limits.
- [x] Verify observable repaired behavior before moving the milestone/tasks to done through /pm.

## Source + Goal linkage

- **Source:** Promoted W4/273 after its deployed recheck, independently reproduced JournalFilters/default Tabs extensions, and separate Calendar, Billing cycle, Net Worth view, Budget, Accounts and ledger-creation radio selected-cue controls, October 20–21 dashboard QA. Original evidence is preserved in [FINDINGS.md](./FINDINGS.md).
- **Goal linkage:** **A2 — Frictionless onboarding:** keyboard and contrast-theme readers must read the active bookkeeping choice before Enter, Space or a pointer action applies it.
- **Expected outcome:** Account/year/ledger choices, Journal filters, directive/report tabs, calendar dates, Billing cycle, Net Worth representation, Budget filters, Accounts type and creation radio cards retain readable labels/icons and visible selected state.
- **Why now:** The moving-highlight repair is deployed, but PNG inspection reveals solid text backplates masking labels and independently absent Calendar/Billing/Net Worth/Budget/Accounts/creation-radio selected cues. Ten styling targets, state-versus-focus checks, real caller checks, dark/theme-order preservation and rendered regressions exceed the original sub-hour note. Adoption surface is included because the change affects user-facing controls.

## Scope and dedupe

Own selected CommandItem/Combobox option styles, journal-filter-button-state.ts and default TabsTrigger styles. Preserve indicators shipped by 7c4e21f4f, 68ea256fc and cae07deb7; the residual is label paint. Historical [131](../131.md) and [133](../133.md) point here for their independently confirmed residual, with no parallel implementation items. W4/273's complete original/deployed records remain in FINDINGS.md. No financial calculation, API, dependency, whole-page adaptation or upstream selection/focus rewrite.

[t006](./done/t006.md) separately owns CalendarDayButton's missing forced-color selected-day cue. Its author palette collapses without an explicit selected-state cue; this is independently reproduced and is a different mechanism from the text backplates above. Shared contrast acceptance and label-preserving palette treatment stay in this milestone. [298](../298.md) owns the same Calendar wrapper's independent RTL direction bridge; neither task depends on rewriting the other.

[t007](./done/t007.md) separately owns the Billing PlanPicker cycle's missing selected cue. Its two labels remain readable while both pressed-state images become identical under forced colors. Preserve the real local cycle/price behavior and native focus; no plan action or subscription mutation is part of this style repair.

[t008](./done/t008.md) separately owns NetWorthCard's persistent Chart/Table selected cue. The current W4/086 pressed semantics and real renderer/URL changes pass; the selected-control images still become identical under forced colors. Keep the repair local to these semantic view controls rather than redefining every secondary Button.

[t009](./done/t009.md) owns the shared BudgetFilterPills treatment used by Interval and Time span. [t010](./done/t010.md) owns Accounts' type buttons: their transparent inactive borders become visible in forced colors, so a border alone does not distinguish the selection. Both were independently tested; their labels and filtering remain correct. Extend this existing contrast milestone rather than opening overlapping inbox findings or changing the shared Button's action semantics.

[t011](./done/t011.md) owns LedgerForm's start-kind and preset radio-card treatment. Native checked semantics change correctly while their author fills/borders/rings lose the persistent cue; the sr-only inputs supply no visible native marker. Both groups were independently exercised in ordinary and forced themes. W4/314–317 own that form's separate behavior defects; this task changes selection paint only and does not submit the wizard.

## Closeout (2026-10-22)

- **Implementation:** `forced-selected` in `dashboard/src/style.css` opts only a selected control out of forced-colour adjustment and keeps the user's system pair (`Highlight`/`HighlightText`, important against `dark:` and hover rules), with no shadow and with readable descendants. Each control adds it behind its own state:
  - CommandItem `data-[selected=true]:`, Combobox `aria-selected:` and default Tabs `data-[state=active]:`;
  - Journal filters, through the pressed branch;
  - Calendar `data-[selected-single=true]:`;
  - Billing cycle, Net Worth view, Budget pills and Accounts type, all `aria-pressed:`;
  - creation cards `has-[:checked]:`, which also gain a forced-colors focus outline.

  Unselected controls, underline tabs and ordinary themes keep their rendering. No global opt-out, no Button change and no dependency.
- **Evidence:** a local production build in Chromium 155 forced-colors emulation, light and dark, at 1440 and 390 px, against replayed public reads.
  - All 44 surface cases read on real screenshot label regions (39–226 colours). Re-enabling adjustment on the same element reproduces the solid backplate (2–7 colours).
  - The Calendar's committed day stays highlighted while focus outlines another day.
  - 21 new or changed regressions fail with the sources and stylesheet reverted ([t004](./done/t004.md)).
- **Gates:** dashboard `yarn format:check`, `yarn lint`, `yarn test` (639 files, 6679 tests) and `yarn build` pass.
- **Target and limits:**
  - Verified locally, not on the deployed site. QA should repeat FINDINGS.md's production checks after deployment.
  - Physical Windows contrast themes, other engines and speech were not verified.
  - Compatibility-scope callers were not exercised individually: the other Combobox wrappers and DatePicker callers, the other default-Tabs owners, the welcome LedgerForm, and non-Free Billing states.
  - Preset cards gained the start cards' ordinary-theme focus ring.
  - The fixture recorded reads only, and no hosted write was made. Nothing private entered the board.
