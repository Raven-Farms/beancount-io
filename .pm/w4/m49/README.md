# w4 · m49 — Keep entry-source saves within their pending draft session

**Worker:** worker1 **Goal:** an earlier entry-source save cannot discard accepted pending input or close a newer entry draft. **Status:** todo

**Severity:** major client draft loss. **Estimate:** 180m across six tasks, dashboard only. Reproduction uses guarded writes with local acknowledgements or pre-transport aborts; stored ledger changes are not claimed.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Protect entry-source input through pending writes | 45m | — |
| [t002](./t002.md) | Keep obsolete completion from consuming a newer entry dialog | 45m | t001 |
| [t003](./t003.md) | Verify entry editing adoption surfaces and preserved workflows | 15m | t002 |
| [t004](./t004.md) | Simplify the bounded entry pending/session repair | 15m | t003 |
| [t005](./t005.md) | Prove source ownership through success, failure and reopening | 45m | t003 |
| [t006](./t006.md) | Verify repaired journeys and archive the milestone | 15m | t004, t005 |

## Definition of done

- [ ] A held entry-source Save accepts no input that its acknowledgement will silently discard, or retains every newer accepted edit. Readable source, truthful pending state and one in-flight request remain available.
- [ ] Closing/discarding a pending old entry and opening/editing a different entry cannot let the old completion close, reset or invalidate away that new draft. A bounded pending-dismissal lock is acceptable; an ownership approach must also preserve the active draft through cache refresh.
- [ ] A genuine failed Save retains the exact current source, useful error/retry and normal dirty state. One deliberate retry submits that current source once.
- [ ] Ordinary Keep editing/Discard, source navigation, clean dismissal, successful own-session completion, returned entry identity, stale-SHA refusal/copy recovery, write-outcome warnings and useful focus retain their behavior.
- [ ] Meaningful actual editor/dialog regressions and fresh desktop/narrow guarded controls cover the reproduced boundaries. Audit shared modal entrypoints, standalone EntryPage and pending deletion without claiming those untested paths are broken.
- [ ] Adoption/simplification/test review and dashboard gates pass; /pm archives only after the observable end state holds.

## Source + Goal linkage

- **Source:** continuous $qa-find-bugs-dashboard,2026-10-22; [reproductions and controls](./FINDINGS.md).
- **Goal linkage:** **A2 — Frictionless onboarding.** Someone correcting a ledger entry must be able to trust its pending Save and the draft currently displayed.
- **Expected outcome:** source editing respects one submitted snapshot and one active dialog lifetime, including genuine failure and deliberate retry.
- **Why now:** both widths accept later source edits that disappear at a modeled acknowledgement, and an old save also closes a different entry's new dirty dialog. Input locking, dialog/cache ownership and meaningful regressions exceed an hour. Adoption review is included because Journal, Overview and Account expose this editing surface.

## Scope and dedupe

Own EntryContextMain/Panel and EntryContextDialog integration, preserving their Journal/Overview/Account modal callers and standalone EntryPage. [W3/565](../../w3/done/565.md) covers user-requested dirty dismissal; [251](../done/251.md) covers returned identity after standalone save; [307](../done/307.md) covers stale-draft copy feedback. File [241](../done/241.md)/[247](../done/247.md), New Entry [M33](../done/m33/README.md), settings [M47](../done/m47/README.md) and receipt [M48](../m48/README.md) own different implementations. No backend/API, automatic resend, persistent draft store, global mutation observer or dependency change.
