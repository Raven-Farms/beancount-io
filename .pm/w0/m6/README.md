# w0 · m6 — Every app-mediated ledger write enforces the directive limit at one boundary

**Worker:** worker1 **Goal:** the free-tier directive limit is checked once, at the ledger service's common commit boundary and on pull-request merge, instead of in selected route handlers, so a source-slice edit or a merged pull request cannot grow a ledger past it **Status:** todo (t001–t002 done)

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | Check the projected directive count inside `commitLedgerFiles` | 60m | — | — **DONE**
| t002 | Pull-request merge refuses a head that would exceed the limit | 45m | t001 | — **DONE**
| t003 | Contract tests for the source-slice refusal on REST, GraphQL and MCP | 30m | t001 |
| t004 | Adoption surface | 20m | t002, t003 |
| t005 | Simplify | 15m | t004 |
| t006 | Test coverage | 30m | t004, t005 |
| t007 | Closeout | 10m | t006 |

## Definition of done

- A source-slice update that replaces one entry with enough directives to cross a free ledger's limit is refused with `directive_limit_exceeded` (403) on REST, GraphQL and MCP alike, and nothing is committed.
- Merging a pull request whose head would cross the limit is refused with the same error; merging one that stays under it, or that shrinks the ledger, works as before.
- The per-route `checkDirectiveLimitForFileChanges` calls in `api/files.ts` and `api/entries.ts` are gone or reduced to what the commit boundary does not cover, with the reason written next to any that remain.
- Deletions and changes that do not raise the count still pass when a ledger is already over the limit.
- `surface-parity.test.ts` keeps `gql: 0`, `rest: 0`, `mcp: 0`; ledger and backend-v2 gates pass.

## Source + Goal linkage

- **Source:** security review of `main` (2026-10-18). `updateSourceSlice` (`backend-cluster/ledger/src/features/ledger/service/ledger-journal-service.ts:900-947`, route `api/journal.ts:118`) goes `commitTransforms` → `commitLedgerFiles` (`features/ledger/operations/commit-ledger-files.ts:144`) with no limit check, and `new_content` is unrestricted. The check lives only in route handlers: `api/files.ts:152,185,249` and `api/entries.ts:250`. backend-v2's `PullRequestService.mergePR` (`features/gitea/pull-request/service/pull-request-service.ts:546-567`) merges through Gitea with no count at all. Git push is gated separately and by design only blocks a ledger that is already over the limit (`features/gitea/policy/directive-limit-gate.ts`, ADR 0005 in the ledger README); that stays.
- **Goal linkage:** **A1 — Agent-native accounting.** Agents edit ledgers through MCP `updateEntrySource` and pull requests; the same write should get the same answer on every surface, as the parity rule requires.
- **Expected outcome:** a free ledger's limit means one thing on every app-mediated write path, and a contributor adding a new write path inherits the check instead of having to remember it.
- **Why now:** fixing source-slice alone would leave the pull-request route open, so both move to shared boundaries together. Sequenced after [m5](../done/m5/README.md), because counting at the commit boundary runs the count on more paths.
- **Adoption surface:** included. The REST v1 docs, the OpenAPI snapshot and the MCP tool descriptions for source-slice edits and pull-request merge gain a documented refusal.
