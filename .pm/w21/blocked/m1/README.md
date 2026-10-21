# w21 · m1 — Entry edits and deletes refuse changes that would break the ledger

**Worker:** worker1 **Goal:** editing or deleting an existing entry can't silently add a bean-check error. Since w0/m2, adding an entry is refused unless the caller passes `allowInvalid`. The edit and delete source-slice writes still commit whatever they are given, and the native app then reports plain success. **Status:** blocked (t001–t006 done; t007 Closeout awaits the deployed check)

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | Ledger service refuses source-slice updates and deletes that add bean-check errors — **DONE** | 60m | — |
| t002 | Same refusal and `allowInvalid` on GraphQL, REST and MCP, with parity tests and docs — **DONE** | 45m | t001 |
| t003 | Mobile Edit Transaction, Delete and the file editor say what a write broke — **DONE** | 45m | t001 |
| t004 | Adoption surface — **DONE** | 20m | t002, t003 |
| t005 | Simplify — **DONE** | 15m | t004 |
| t006 | Test coverage — **DONE** | 30m | t004, t005 |
| t007 | Closeout — **blocked** | 10m | t006 |

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

## Blocked

**Blocked 2026-10-20** — t007 Closeout cannot run here, because the definition of done is observed on the deployed service and the native app.

- **Shipped baseline:**
  - `89e57bfbb` (ledger): source-slice update/delete/multi-delete project their transforms and refuse with `NEW_LEDGER_ERRORS` unless `allowInvalid`. The REST bodies and IDL take `allowInvalid`.
  - `1a5e26adf` (backend-v2): GraphQL, REST v1 and MCP take `allowInvalid` and map the refusal to `VALIDATION_FAILED` + `newLedgerErrors`. Docs, tool descriptions, server instructions and the OpenAPI snapshot are updated.
  - `fbbe4e0be` (mobile): delete keeps the detail screen with a dialog, Edit shows the refusal inline, and the file editor warns on a save that adds errors.
  - `53633026c`: CLI spec sync.
  - `a281d9ffb`: one shared refusal helper.
  - `250c4d2f0`: tests.
- **Verified here:**
  - Ledger: 1393 tests, lint, typecheck and build. `source-slice-new-errors.test.ts` covers the delete and re-date repros with a stub engine, and its refusal cases fail when the guard is removed.
  - backend-v2: 6285 tests including zero-debt surface parity, typecheck and lint. OpenAPI was regenerated and the diff reviewed. `source-slice-parity.test.ts` proves the refusal and the opt-out on REST, GraphQL and MCP, and all 18 cases fail without the change.
  - Mobile: format, tsc, eslint, knip, and 2359 unit tests.
  - CLI: lint, mypy, spec-check and docs-check. Nine pytest cases fail locally with or without these changes (signal-death, price-source limit, release-lock).
  - Dashboard: no code change. It already renders `newLedgerErrors` refusals through `useErrorMessage`.
- **Not verified:** the real rustledger engine on these writes, the deployed REST/GraphQL/MCP surfaces, and the native app. This worker has no deploy access and no simulator QA session.
- **Blocker:** the definition of done needs the ledger service at `89e57bfbb` or later and backend-v2 at `1a5e26adf` or later deployed to `https://beancount.io`, and a native dev build that includes `fbbe4e0be`.
- **Unblock:** after deploy, a QA run on the synthetic disposable ledger `mcp-agent-eval` (with `2026-08-29 balance Assets:Cash 49.75 USD`):
  1. On GraphQL, REST and MCP, deleting the 2026-08-28 FARMERS MARKET entry and re-dating it to 2026-08-30 are each refused with `Balance failed for Assets:Cash …`, and the file sha is unchanged.
  2. The same requests with `allowInvalid: true` commit.
  3. In the native app, both repros keep the detail or editor screen with the refusal readable, and a file-editor save that breaks the assertion warns.
  4. The fixture bytes are restored (sha256-checked, clean `getLedgerErrors`).

  Then run `/pm done w21/m1/t007`. **Who:** the user (deploy) and the mobile/MCP QA loops.

**Partial native check 2026-10-20 (QA loop)** — the API is **not yet deployed**. Production introspection still shows `DeleteSourceSliceInput {entryHash, sha256sum}` and `UpdateSourceSliceInput {entryHash, sha256sum, newContent}`, with no `allowInvalid`, so unblock items 1–2 and the server half of 3 remain open. Verified the client-only part of item 3 on iPhone 17e (iOS 27.0), dev build serving `main` at `d4a3d0906`: a file-editor save that adds `2026-01-02 balance Assets:Cash  1.00 USD` to `mcp-agent-eval` commits, then shows "Saved, with a new ledger error — … Balance failed for Assets:Cash: expected 1.00 USD, got 200.00 USD" with **Close** and **View errors**, plus the "1 error" banner. Restored byte-for-byte, with a clean ledger check.

**Deployed-surface check 2026-10-20 19:30 (QA loop)** — production now exposes `allowInvalid` on `DeleteSourceSliceInput` / `UpdateSourceSliceInput`. On the synthetic disposable ledger `mcp-agent-eval`, with the FARMERS MARKET entry `371532b3…` and `2026-08-29 balance Assets:Cash 49.75 USD`:

| surface | delete | re-date to 2026-08-30 | `allowInvalid: true` |
| --- | --- | --- | --- |
| GraphQL | refused, `VALIDATION_FAILED`, `newLedgerErrors` = "Balance failed for Assets:Cash: expected 49.75 USD, got 73.25 USD (main.bean:84)", sha unchanged | refused the same way (main.bean:87), sha unchanged | both commit |
| REST v1 (`POST …/entry-source/delete`, `PUT …/entry-source`) | HTTP 400 `VALIDATION_FAILED`, message names the balance failure, sha unchanged | HTTP 400, same, sha unchanged | both HTTP 200 and commit |
| Native app, iPhone 17e / iOS 27.0, `main` at `d2b8efbb4` | "Failed to delete transaction — This would add an error to your ledger: Balance failed … (main.bean:84)"; the detail screen stays | inline under the editor hint plus a toast, "This would add an error to your ledger: … (main.bean:87)"; the editor stays | — |
| MCP (`/api-gateway/mcp`) | **not verified**: the endpoint answers 401 to the QA session, and no `QA_MCP_TOKEN` is available to this loop | — | — |

The file-editor warning (item 3) was verified earlier in this section. Every write was restored byte-for-byte (sha256 checked, clean `getLedgerErrors`).

**Unblock (narrowed):** only the MCP arm remains. Run `node .agents/skills/qa-shared/scripts/qa-mcp.mjs --credentials-file <file with QA_MCP_TOKEN>` against `mcp-agent-eval`: the delete and edit source tools refuse both repros, and the same calls with `allowInvalid: true` commit. Then restore and run `/pm done w21/m1/t007`. **Who:** whoever holds the QA MCP token (the user), or the MCP QA loop.
