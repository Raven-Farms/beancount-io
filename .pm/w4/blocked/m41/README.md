# w4 · m41 — Preserve acknowledged actions through refresh failures

**Worker:** worker1 **Goal:** Star and Budget report a confirmed action truthfully even when a subsequent metadata/list read fails. **Status:** blocked (t001, t002 done; t003 and t005 need controlled browser checks)

**Severity:** minor. **Estimate:** 140m across six tasks, dashboard only.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Preserve confirmed Star and Unstar results — **DONE** | 40m | — |
| [t002](./done/t002.md) | Finish an acknowledged Budget submission once — **DONE** | 40m | t001 |
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

## Blocked

**Blocked 2026-10-20** — both repairs shipped; t003 and t005 need fresh controlled-browser runs, so t004 Simplify and t006 Closeout (which follow t003) wait too.

- **Shipped baseline:** `9a268c473` drops the awaited GetLedger refetch from Star/Unstar and writes the acknowledged `isStarred` into the cached ledger (`write-starred-state.ts`), so a failed later read can no longer reject a confirmed star or roll the button back; `success:false` and pre-ack transport failures still roll back with their own message. `292a4321b` drops the awaited GetLedgerJournal refetch from AddBudgetDialog: a `success:true` budget resets, closes and finishes once, then the active list query is refetched without awaiting, so a failed read shows on the Budget page's own error/Retry rather than as an enabled replay of the write. `star-acknowledgement.test.tsx` and `add-budget-acknowledgement.test.tsx` use a real Apollo client with the acknowledgement and every later read controlled separately (Star and Unstar, true/read-fail, success:false, transport failure; Budget true/read-fail, success:false, transport failure); both fail with the repair reverted. Dashboard format, lint, test and build pass. Note 295 (Budget pending-draft ownership) is a separate item in the same dialog.
- **Blocker:** t003/t005 require fresh 1440 and 390 controlled-browser runs on Overview and Budget with pre-transport mutation responses and a failed follow-up read; no browser is available to this worker.
- **Unblock:** after `292a4321b` or later is deployed, QA repeats FINDINGS.md's controlled Star (and Unstar) and Add Budget runs at 1440 and 390: after a schema-complete `success:true` and an aborted read, Star stays **Starred** with the success toast and Budget closes with a single intercepted write; the successful-read, `success:false` and transport-failure controls keep their behavior; then close t003/t005, run t004's /simplify and t006. **Who:** the user (deploy) and the dashboard QA loop.

