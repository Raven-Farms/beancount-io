# w1 · m38 — One MCP tool per operation, so the ChatGPT app directory accepts every tool

**Worker:** worker1 **Goal:** Every model-callable MCP operation is its own tool with its own description, input schema, and annotations. No tool dispatches on an `operation` argument. OpenAI's app-directory scan then reports no blocking findings, and parity, the frozen baseline, prompts, and docs describe the new shape. **Status:** in progress (t001–t006 done)

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Decide the split: tool names, annotations, and the ADR amendments — **DONE** | 45m | — |
| [t002](./done/t002.md) | Split the bank tools: `manageBankImport` and `manageBankConnection` — **DONE** | 60m | t001 |
| [t003](./done/t003.md) | Split ledger lifecycle, collaborators, and pull requests — **DONE** | 60m | t001 |
| [t004](./done/t004.md) | Split the editing tools: `editLedgerFiles` and `editEntrySource` — **DONE** | 60m | t001 |
| [t005](./done/t005.md) | Retire the grouped-dispatcher machinery and remeasure the tool-list gates — **DONE** | 40m | t002, t003, t004 |
| [t006](./done/t006.md) | Update prompts, docs, and skills that name the old tools — **DONE** | 45m | t002, t003, t004 |
| t008 | Adoption surface | 30m | t005, t006 |
| t009 | Simplify | 30m | t008 |
| t010 | Test coverage | 45m | t008, t009 |
| t007 | Verify on production: OpenAI rescan and Claude portal tools step | 20m | t010 |
| t011 | Closeout | 15m | t007, t010 |

Re-sequenced 2026-10-18: production verification (t007) moved after Test coverage (t010). Adoption surface, Simplify, and Test coverage need no deploy. Verifying last means the directories check the revision that closes the milestone.

## Definition of done

- No tool in `tools/list` has an `operation` discriminator. Each former branch is its own tool, with a title, a description, its own input schema, and annotations that match it: `readOnlyHint`, plus `destructiveHint: true` for deletion, overwriting, cancellation, or access revocation.
- Every affected verb in `VERB_TABLE` binds to its own MCP tool, and `surface-parity` stays at zero gaps. The frozen parity baseline's 11 rows that named `editLedgerFiles`, `manageBankConnection`, or `manageBankImport` are covered by an explicit, commented rename map in `parity-baseline.test.ts`. The fixture stays unedited.
- ADR 0008 has an amendment reversing D3 ("grouped by shape"), and ADR 019 has an amendment quoting OpenAI's finding. `docs/mcp.md`, `docs/api-parity.md`, the MCP prompts, the skills, the README counts, and a release note name only the new tools.
- The tool count and `tools/list` size gates are remeasured and justified in the change that moves them.
- After the operator deploys, the OpenAI Plugins dashboard rescan of the Beancount.io draft shows no "operations that are not individually exposed" finding, and Claude's portal Tools step lists the new tools. Both are recorded with date and revision.

## Source + Goal linkage

- **Source:** OpenAI Plugins dashboard scan of the Beancount.io draft, 2026-10-18. Seven tools (`editLedgerFiles`, `editEntrySource`, `manageBankImport`, `manageBankConnection`, `managePullRequests`, `manageLedgers`, `manageLedgerCollaborators`) received: "This tool appears to execute operations that are not individually exposed. Please expose each model-callable operation upfront as a separate tool with a clear description, input schema, and annotations." `manageLedgers` also received "This new tool definition needs further review before it can be published." Claude's review criteria point the same way: "Ideally, split write operations further by action type: create, update, and delete."
- **Goal linkage:** **A3: community and distribution** (primary). These findings are the remaining blocker between the draft and the ChatGPT app directory. A listing there and in Claude's directory is the owner's top adoption goal (2026-10-09). **A1** (secondary): granular tools carry accurate per-operation annotations, so hosts auto-approve reads and confirm only real destructive actions.
- **Expected outcome:** the ChatGPT submission passes automated checks, and both directories see precise per-operation tools. Signal: zero blocking findings on rescan, then directory acceptance.
- **Why now:** this is the last code-side blocker for the ChatGPT submission. It deliberately reverses ADR 0008 D3, which grouped tools to keep `tools/list` small, because directory acceptance outranks tool-count economy (owner decision 2026-10-09). The renamed tools break MCP clients that call the old names; the release note and docs cover that. Adoption surface is included because every connecting agent sees the new tool list.
