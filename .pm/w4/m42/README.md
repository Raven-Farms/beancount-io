# w4 · m42 — Keep keyboard focus owned during and after modal submissions

**Worker:** worker1 **Goal:** Keyboard users stay inside a pending entry dialog and retain a useful position when a submission fails. **Status:** todo

**Severity:** minor. **Estimate:** 110m across five tasks, dashboard only.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Keep submission focus inside its dialog through pending and failure | 40m | — |
| [t002](./t002.md) | Verify keyboard recovery across submission adoption surfaces | 20m | t001 |
| [t003](./t003.md) | Simplify the bounded focus integration | 10m | t002 |
| [t004](./t004.md) | Prove pending containment and failed-submit focus ownership | 30m | t002 |
| [t005](./t005.md) | Close out and archive the milestone | 10m | t003, t004 |

## Definition of done

- [ ] In real desktop/narrow New Entry, a valid native submission remains single-flight and locks its fields while keyboard Tab/Shift+Tab stays inside the visible modal. Pending focus cannot reach the background Query link.
- [ ] After a controlled pre-transport failure, the same accepted draft and controls remain usable and focus returns to the originating or explicit recovery control, without restarting at the directive tabs.
- [ ] A deliberate move to another enabled modal control, including the pending Close control, retains its focus. Success, actual dismissal and obsolete dialog lifetimes do not receive a stale focus handoff.
- [ ] Preserve the shared hook's six current callers: four New Entry forms, Accounts Open Account and Budget. Keep exact values, validation, pending input/dismissal protection, duplicate-submit guards, truthful errors and successful return focus.
- [ ] Meaningful real Dialog/form regressions and native browser controls fail against the current lifecycle and pass after repair; dashboard format/lint/test/build pass. Distinguish deployed checks from local ones and record unexercised callers/platforms.
- [ ] No global focus manager, copied upstream focus trap, newly enabled pending field, backend/API change or new dependency is needed; archive through /pm only when the observable behavior holds.

## Source + Goal linkage

- **Source:** Continuous dashboard QA requested for w4, 2026-10-20; [fresh live controls and source comparison](./FINDINGS.md).
- **Goal linkage:** **A2 — Frictionless onboarding:** a keyboard reader entering bookkeeping data must keep their place during a slow or failed action and remain in the dialog that owns it.
- **Expected outcome:** A held or failed entry submission keeps the user's keyboard in the active workflow, with preserved draft and a usable retry position.
- **Why now:** The existing pending/draft repairs correctly retain text but their focus behavior still fails in a real modal. Native reverse-Tab can reach the background while the write is held. Bounded shared submission integration, meaningful portal/native-focus regressions and six-caller preservation exceed an hour. Adoption verification is included because this is a customer-facing keyboard contract.

## Scope and dedupe

Own the pending/settled focus lifecycle at `common/hooks/use-pending-submit.ts` and the necessary owning Dialog/form integrations. New Entry Note is independently reproduced at both widths; the other five current hook callers are compatibility/audit scope until exercised. Completed [m33](../done/m33/README.md), [284](../done/284.md) and [295](../done/295.md) retain their draft/serialization work; this is its remaining focus boundary. Open [m35](../blocked/m35/README.md) concerns a separate suggestions Retry helper, not a form submission. No persistent draft store, broad Radix rewrite or bank/credential action.
