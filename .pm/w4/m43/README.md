# w4 · m43 — Keep active contrast-theme labels readable

**Worker:** worker1 **Goal:** Readers can identify the selected option, filter or tab before activating it in a contrast theme. **Status:** todo

**Severity:** minor. **Estimate:** 120m across five tasks, dashboard only.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Preserve readable active labels across the four styling targets | 45m | — |
| [t002](./t002.md) | Verify the contrast behavior on its adoption surfaces | 25m | t001 |
| [t003](./t003.md) | Simplify the bounded contrast repair | 10m | t002 |
| [t004](./t004.md) | Prove actual label paint and preserve selection regressions | 30m | t002 |
| [t005](./t005.md) | Close out and archive the milestone | 10m | t003, t004 |

## Definition of done

- [ ] Under real browser forced-colors emulation, the active cue and actual label remain readable for CommandItem, shared Combobox options, pressed JournalFilters and default pill Tabs. Check light/dark at desktop/narrow widths on applicable real consumers, after transitions settle and while keyboard selection moves.
- [ ] Preserve the user's system palette, inactive labels, ordinary themes, dimensions, separate focus cues, pointer behavior and selection models. Any local adjustment exception must keep explicit system foreground/background values effective, including dark/theme overrides and descendant labels; no page-wide forced-color opt-out.
- [ ] Account and ledger targets, report year, Journal filters and directive tabs still apply the same values. Preserve input focus/active descendants, native dialog return focus, retained account period and intentional cross-ledger filter clearing. No hosted write is necessary.
- [ ] Preserve readable dark pill tabs, native Select options, underline profile tabs, shared Button focus, Switch and custom-row repairs. Audit callers and distinguish tested aliases from compatibility scope.
- [ ] Meaningful paint/selection regressions expose the current unreadable text. Existing class/CSS checks are not the only visibility evidence. Dashboard format/lint/test/build pass; record actual browser evidence and limits.
- [ ] Verify observable repaired behavior before moving the milestone/tasks to done through /pm.

## Source + Goal linkage

- **Source:** Promoted W4/273 after its deployed recheck and independently reproduced JournalFilters/default Tabs extensions, October 20–21 dashboard QA. Original evidence is preserved in [FINDINGS.md](./FINDINGS.md).
- **Goal linkage:** **A2 — Frictionless onboarding:** keyboard and contrast-theme readers must read the active bookkeeping choice before Enter, Space or a pointer action applies it.
- **Expected outcome:** Active account/year/ledger choices, Journal filters and directive/report tabs show readable labels alongside their state indicator.
- **Why now:** The moving-highlight repair is deployed, but PNG inspection reveals solid text backplates masking labels. Four styling targets, real caller checks, dark/theme-order preservation and rendered regressions exceed the original sub-hour note. Adoption surface is included because the change affects user-facing shared controls.

## Scope and dedupe

Own selected CommandItem/Combobox option styles, journal-filter-button-state.ts and default TabsTrigger styles. Preserve indicators shipped by 7c4e21f4f, 68ea256fc and cae07deb7; the residual is label paint. Historical [131](../done/131.md) and [133](../done/133.md) point here for their independently confirmed residual, with no parallel implementation items. W4/273's complete original/deployed records remain in FINDINGS.md. No financial calculation, API, dependency, whole-page adaptation or upstream selection/focus rewrite.
