# w4 · m47 — Keep profile saves within their submitted dialog session

**Worker:** worker1 **Goal:** one pending Change Name save cannot create duplicate writes or consume a newer accepted draft. **Status:** todo

**Severity:** minor. **Estimate:** 165m across six tasks, dashboard only. All reproduced writes were intercepted or locally modeled; no hosted profile change or remote overwrite was observed.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Guard every Change Name submission path while pending | 45m | — |
| [t002](./t002.md) | Keep pending inputs and dialog completion in the same draft session | 45m | t001 |
| [t003](./t003.md) | Verify the profile editing adoption surface | 15m | t002 |
| [t004](./t004.md) | Simplify the bounded pending-session repair | 15m | t003 |
| [t005](./t005.md) | Prove duplicate-submit and dialog-lifetime recovery | 30m | t003 |
| [t006](./t006.md) | Verify repaired journeys and archive the milestone | 15m | t004, t005 |

## Definition of done

- [ ] Holding one Change Name save, Save and Enter in either input start no second UpdateProfile. A deliberate settled retry starts exactly one request with current trimmed values.
- [ ] Pending input and dismissal/reopening follow a coherent draft policy: no accepted correction silently disappears, and an obsolete success never resets or closes a newer draft. A bounded pending lock is sufficient.
- [ ] Real failure preserves the submitted draft, useful error/retry behavior and usable focus. Ordinary idle Cancel, successful own-session completion, the composing-Enter guard and profile refetch behavior remain correct.
- [ ] The adjacent Username callback is audited for the same protection; preserve username validation, IME handling and existing account policy. No real username change is needed for verification.
- [ ] Meaningful component/dialog regressions and fresh desktop/narrow browser controls cover the reproduced transitions. Existing dashboard gates pass; simulated results are labeled and no actual account changes are required.
- [ ] Documentation/adoption guidance stays accurate, simplification/test review completes, and /pm archives only after the observable behavior holds.

## Source + Goal linkage

- **Source:** continuous $qa-find-bugs-dashboard,2026-10-22; [reproductions and controls](./FINDINGS.md), promoted from inbox975 after its same-controller dialog-lifetime repeat expanded the work beyond an hour.
- **Goal linkage:** **A2 — Frictionless onboarding.** Account editing should honor one pending save and protect what the reader is currently entering.
- **Expected outcome:** a keyboard user can save a name once, wait/retry safely and continue editing without an earlier completion erasing another draft.
- **Why now:** both widths reproduce concurrent keyboard requests despite disabled Save, and a locally modeled old success closes a newly opened draft. Submit guarding plus input/dialog ownership and real regressions exceed one hour. Adoption review is included because the edited dialog is customer-facing.

## Scope and dedupe

Own UserProfileSection and its bounded pending/dialog integration. [296](../done/296.md) supplies the existing composition guard; [M33](../done/m33/README.md) and [M42](../done/m42/README.md) cover separate entry/account/budget callers, not settings. [973](../973.md) owns the standalone receipt form. No backend/API, persistent draft store, global mutation observer or dependency change. Actual profile persistence, server write ordering, refetch failure and other engines remain unverified.
