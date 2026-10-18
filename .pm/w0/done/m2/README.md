# w0 · m2 — Structured ledger writes refuse changes that would break the ledger

**Worker:** worker1 **Goal:** no client can commit a structured entry that introduces a bean-check error without saying so: GraphQL, REST and MCP refuse it the way the text-append route already does, unless the caller passes `allowInvalid` **Status:** done

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | Shared writer refuses structured writes that add bean-check errors | 60m | — | — **DONE**
| t002 | Same refusal on GraphQL `bulkEntries`, REST `POST …/entries` and MCP `addLedgerEntries`, with contract tests and docs | 45m | t001 | — **DONE**
| t003 | Mobile and dashboard write forms show the refusal message | 30m | t001 | — **DONE**
| t004 | Adoption surface | 20m | t002, t003 | — **DONE**
| t005 | Simplify | 15m | t004 | — **DONE**
| t006 | Test coverage | 30m | t004, t005 | — **DONE**
| t007 | Closeout | 10m | t006 | — **DONE**

## Definition of done

- A structured write that adds a bean-check error (for example a second `open` for an account the ledger already opens, error E1002) is refused on GraphQL, REST and MCP alike. Nothing is committed, and the response names the first new error.
- The same request with `allowInvalid: true` commits and reports the new errors.
- A write that adds no error behaves exactly as before.
- `surface-parity.test.ts` keeps `gql: 0`, `rest: 0`, `mcp: 0`; the OpenAPI snapshot is regenerated; backend-v2, mobile and dashboard gates pass.

## Source + Goal linkage

- **Source:** `/pm-brainstorm` for w0 (2026-10-17), built on w0/037's optional backend hardening and the root cause in w3/640. The text-append route already refuses new errors unless `allowInvalid` (`backend-v2/src/features/ledger/workflow/directive-append-workflow.ts:174`, `utils/directive-text-contract.ts`). Structured writes only check transaction balance before committing (`backend-cluster/ledger/src/api/entries.ts`, the `checkTransactionBalance` gate), and MCP reports new errors after the fact (`ai-agent/api/mcp-tools.ts`, `withPostWriteValidation`).
- **Goal linkage:** **A1 — Agent-native accounting.** An agent maintaining a ledger through MCP or the REST API gets a clean refusal it can act on, instead of a committed, broken ledger it has to notice and repair.
- **Expected outcome:** coding agents and API clients cannot break a hosted ledger with a single structured write by accident; the mobile and dashboard forms that guard client-side (w0/037, w3/557) have a server-side backstop.
- **Why now:** two clients just fixed one way each to write a broken ledger; the shared boundary is the place that covers every client, including MCP agents. This is a contract change for structured writes (report → refuse), aligned with the existing text-append semantics. If it lands, w3/640 narrows to the dashboard warning for deliberate `allowInvalid` writes, and w3/641 (amount syntax) stays as is.
- **Adoption surface:** included. The MCP tool description, the REST v1 docs and the API parity contract change.
