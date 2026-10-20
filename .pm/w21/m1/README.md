# w21 · m1 — Entry edits and deletes refuse changes that would break the ledger

**Worker:** worker1 **Goal:** editing or deleting an existing entry can't silently add a bean-check error. Since w0/m2, adding an entry is refused unless the caller passes `allowInvalid`. The edit and delete source-slice writes still commit whatever they are given, and the native app then reports plain success. **Status:** in progress (t001–t005 done)

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | Ledger service refuses source-slice updates and deletes that add bean-check errors — **DONE** | 60m | — |
| t002 | Same refusal and `allowInvalid` on GraphQL, REST and MCP, with parity tests and docs — **DONE** | 45m | t001 |
| t003 | Mobile Edit Transaction, Delete and the file editor say what a write broke — **DONE** | 45m | t001 |
| t004 | Adoption surface — **DONE** | 20m | t002, t003 |
| t005 | Simplify — **DONE** | 15m | t004 |
| t006 | Test coverage | 30m | t004, t005 |
| t007 | Closeout | 10m | t006 |

## Definition of done

- On a ledger with `2026-08-29 balance Assets:Cash 49.75 USD`, both of these are refused on GraphQL, REST and MCP alike: deleting the 2026-08-28 Cash transaction, and moving it to 2026-08-30. Nothing is committed, and the error names the new `Balance failed for Assets:Cash …` message the same way w0/m2's `NewLedgerErrorsError` does.
- The same requests with `allowInvalid: true` commit.
- An edit or delete that adds no error behaves exactly as before. Errors that already existed don't block the write.
- In the native app, the two repros below end with the form or detail screen still open and the refusal readable on screen, not "Transaction saved" / "Transaction deleted". A file-editor save that leaves new errors says so.
- `surface-parity.test.ts` keeps `gql: 0`, `rest: 0`, `mcp: 0`; the OpenAPI snapshot is regenerated; ledger, backend-v2, mobile and dashboard gates pass.

## Evidence (mobile QA, 2026-10-20)

`main` at `ab6f2adf7`, dev build `io.beancount.ios` 1.20261002.50 on iPhone 17e / iOS 27.0, QA account on `https://beancount.io`, synthetic disposable ledger `mcp-agent-eval`. Each write was restored byte-for-byte afterwards (sha256 checked, clean `getLedgerErrors`).

1. **Delete.** Transactions → `FARMERS MARKET` (2026-08-28, `Assets:Cash -23.50 USD`) → **⋯** → **Delete** → **Delete**. The toast says **"Transaction deleted"** and the row disappears. `getLedgerErrors` then returns `main.bean:84 Balance failed for Assets:Cash: expected 49.75 USD, got 73.25 USD`, and the Home bell gets a badge. The only change to the file is the removed block.
2. **Edit.** The same transaction → pencil → change the date line to `2026-08-30` → **Save**. The toast says **"Transaction saved"**, but the ledger now has the same balance failure (`main.bean:87`). That screen's own helper text says *"A stale checksum or invalid beancount will be rejected with an error."*
3. **Control.** New Transaction with a 2026-08-25 Cash posting of −5.00 is refused with "This would add an error to your ledger: Balance failed for Assets:Cash …". So `addEntries` is guarded (w0/m2), and the gap is specific to source-slice writes.

## Root cause

- `backend-cluster/ledger/src/features/ledger/service/ledger-journal-service.ts`: `deleteSourceSlice` (line 788), `deleteMultiSourceSlices` (835) and `updateSourceSlice` (904) call `commitTransforms` directly. None of them projects the result through `checkProjectedErrors` the way `backend-cluster/ledger/src/api/entries.ts:223-247` does before committing.
- MCP's `editEntrySource` / delete tools wrap the same calls in `withPostWriteValidation` (`backend-cluster/backend-v2/src/features/ai-agent/api/mcp-source-slices.ts:54`). They report new errors *after* the commit, so an agent learns the ledger is broken only once it already is.
- The dashboard covers this after the fact with `useWriteOutcome` (w3/640). Mobile has no equivalent: no screen compares ledger errors before and after a write.

## Fix

- t001: run the same projected-error check before the commit in `updateSourceSlice`, `deleteSourceSlice` and `deleteMultiSourceSlices`. Use the transformed file content as the overlay and throw `NewLedgerErrorsError` when `newLedgerErrors(before, after)` is non-empty. Accept `allowInvalid` on all three. Keep the existing CAS / stale-checksum behavior, and check before the directive-limit step, matching `entries.ts`.
- t002: thread `allowInvalid` through the GraphQL mutations (`updateLedgerEntrySourceSlice`, `deleteLedgerEntrySourceSlice`, `deleteMultipleLedgerEntrySourceSlices`), REST `PUT/DELETE …/source-slice(s)` and the MCP source-slice tools. Map the refusal to `VALIDATION_FAILED` + `extensions.newLedgerErrors` exactly as w0/m2 did. Update the API docs and MCP tool descriptions.
- t003: on mobile, Edit Transaction already renders `outcome.message` inline. Confirm it shows the refusal through `describeLedgerRefusal`. The transaction-detail delete must keep the screen and show the refusal in an alert or inline, not a 2-second toast (see `w21/001`). The file editor (`updateLedgerFile`, unguarded by design for raw saves) should warn after a save that adds errors, the way the dashboard's `useWriteOutcome` does, naming the first new error.

## Source + Goal linkage

- **Source:** mobile QA run 2026-10-20 (`/qa-find-bugs-mobile w21`), the repros above. It extends w0/m2 (done), which deliberately covered only structured adds, and w3/640 (done), which added the dashboard's after-the-fact warning.
- **Goal linkage:** **A1 — Agent-native accounting.** An agent editing or deleting entries through MCP or REST gets a refusal it can act on, instead of a broken ledger and a post-hoc validation note. **A2:** native-app users stop being told "saved" / "deleted" when the write just broke their balance assertions.
- **Expected outcome:** no client can break a hosted ledger by accident with a single edit or delete. Every structured write path (add, edit, delete) shares one refusal contract and one opt-out.
- **Why now:** w0/m2 shipped the refusal for adds three days ago, so add and edit now disagree. An edit can produce exactly the state an add is refused for. The shared contract and error mapping already exist, so this is the cheapest moment to close the gap.
- **Adoption surface:** included. The REST v1 docs, MCP tool descriptions and API parity contract change.

## Out of scope

- Refusing raw `updateLedgerFile` saves. The file editor is the escape hatch for hand-repair and may need to pass through invalid states; it gets a warning, not a refusal.
