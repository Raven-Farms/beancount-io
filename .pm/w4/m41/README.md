# w4 · m41 — Preserve acknowledged actions through refresh failures

**Worker:** worker1 **Goal:** Star and Budget report a confirmed action truthfully even when a subsequent metadata/list read fails. **Status:** in progress (t001 done)

**Severity:** minor. **Estimate:** 140m across six tasks, dashboard only.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Preserve confirmed Star and Unstar results — **DONE** | 40m | — |
| [t002](./t002.md) | Finish an acknowledged Budget submission once | 40m | t001 |
| [t003](./t003.md) | Verify action feedback and recovery across adoption surfaces | 10m | t002 |
| [t004](./t004.md) | Simplify acknowledgement and refresh handling | 10m | t003 |
| [t005](./t005.md) | Prove write/read failure boundaries with real Apollo | 35m | t003 |
| [t006](./t006.md) | Close out and archive the milestone | 5m | t004, t005 |

## Definition of done

- [ ] A successful Star/Unstar acknowledgement retains its confirmed isStarred state and truthful feedback if GetLedger then fails; it is not rolled back as an unacknowledged write.
- [ ] An acknowledged Add/Update Budget completes once even if its later Journal read fails. Recovery concerns the read and does not offer the same write again as if it failed.
- [ ] success:false and genuine pre-ack transport failures retain appropriate error feedback, state rollback/draft preservation and retry direction. Pending protection and accessible action names remain intact.
- [ ] Refresh success/failure, cached state and subsequent actions stay coherent. Preserve exact Budget amounts, civil dates, query pagination, independent file-workflow fixes and existing component ownership.
- [ ] Meaningful real-Apollo regressions, fresh desktop/narrow controlled browser checks and dashboard format/lint/test/build pass. No actual social write is required for verification; record response controls and deployment limits.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. [Findings](./FINDINGS.md) preserve W4/294's Star proof and the independently reproduced Budget submission failure. **A2 — Frictionless onboarding / A3 — Community & distribution:** users need trustworthy confirmation before deciding whether to retry an action. Both interfaces currently classify a failed follow-up read as failure of an already acknowledged mutation. Two controllers and independent state/feedback regressions exceed one hour, so the Star inbox note is promoted rather than duplicated. Adoption verification is included because both fixes affect customer actions and recovery.

## Scope

Overview StarButton and its star/unstar hooks, plus AddBudgetDialog's Add/Update consumers. Separate action acknowledgement from metadata refresh using existing response/cache/error contracts. A bounded shared helper is optional only if it improves these real callers; do not add a new mutation framework, import one feature's policy into another or globally remove awaited refetch behavior. No API/schema/parity, dependency or native-mobile change. Preserve completed w3/107 business-failure rollback and W4/248's separate file-write handling.
