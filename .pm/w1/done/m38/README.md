# w1 · m38 — One MCP tool per operation, so the ChatGPT app directory accepts every tool

**Worker:** worker1 **Goal:** Every model-callable MCP operation is its own tool with its own description, input schema, and annotations. No tool dispatches on an `operation` argument. OpenAI's app-directory scan then reports no blocking findings, and parity, the frozen baseline, prompts, and docs describe the new shape. **Status:** done

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Decide the split: tool names, annotations, and the ADR amendments — **DONE** | 45m | — |
| [t002](./done/t002.md) | Split the bank tools: `manageBankImport` and `manageBankConnection` — **DONE** | 60m | t001 |
| [t003](./done/t003.md) | Split ledger lifecycle, collaborators, and pull requests — **DONE** | 60m | t001 |
| [t004](./done/t004.md) | Split the editing tools: `editLedgerFiles` and `editEntrySource` — **DONE** | 60m | t001 |
| [t005](./done/t005.md) | Retire the grouped-dispatcher machinery and remeasure the tool-list gates — **DONE** | 40m | t002, t003, t004 |
| [t006](./done/t006.md) | Update prompts, docs, and skills that name the old tools — **DONE** | 45m | t002, t003, t004 |
| [t008](./done/t008.md) | Adoption surface — **DONE** | 30m | t005, t006 |
| [t009](./done/t009.md) | Simplify — **DONE** | 30m | t008 |
| [t010](./done/t010.md) | Test coverage — **DONE** | 45m | t008, t009 |
| [t007](./done/t007.md) | Verify on production: OpenAI rescan and Claude portal tools step — **DONE** | 20m | t010 |
| [t011](./done/t011.md) | Closeout — **DONE** | 15m | t007, t010 |

Re-sequenced 2026-10-18: production verification (t007) moved after Test coverage (t010). Adoption surface, Simplify, and Test coverage need no deploy. Verifying last means the directories check the revision that closes the milestone.

Blocked 2026-10-18 on the production deploy. Cleared the same day: the user deployed, and `https://beancount.io/.well-known/mcp.json` lists 43 tools with no `manage…`/`edit…` names.

## Definition of done

- No tool in `tools/list` has an `operation` discriminator. Each former branch is its own tool, with a title, a description, its own input schema, and annotations that match it: `readOnlyHint`, plus `destructiveHint: true` for deletion, overwriting, cancellation, or access revocation.
- Every affected verb in `VERB_TABLE` binds to its own MCP tool, and `surface-parity` stays at zero gaps. The frozen parity baseline's 11 rows that named `editLedgerFiles`, `manageBankConnection`, or `manageBankImport` are covered by an explicit, commented rename map in `parity-baseline.test.ts`. The fixture stays unedited.
- ADR 0008 has an amendment reversing D3 ("grouped by shape"), and ADR 019 has an amendment quoting OpenAI's finding. `docs/mcp.md`, `docs/api-parity.md`, the MCP prompts, the skills, the README counts, and a release note name only the new tools.
- The tool count and `tools/list` size gates are remeasured and justified in the change that moves them.
- After the operator deploys, the OpenAI Plugins dashboard rescan of the Beancount.io draft shows no "operations that are not individually exposed" finding, and Claude's portal Tools step lists the new tools. Both are recorded with date and revision.

## Closeout (2026-10-18)

- **No operation selectors.** Production's `/.well-known/mcp.json` lists 43 tools, and no input schema has an `operation`, `op`, `action`, `verb`, `command`, or `method` property. On `main`, `mcp-tool-list.test.ts` enforces the same (t005).
- **Titles, descriptions, schemas, hints.** Every tool carries its title in `annotations`, its own input schema, and all four hints. `mcp-tools.test.ts` pins the destructive and open-world hints ADR 019's table decided (t010).
- **Parity.** Every split verb binds its own tool, and `surface-parity` stays at zero gaps. `RENAMED_ON_MCP` in `parity-baseline.test.ts` covers the frozen baseline's 11 renamed rows; the fixture is unedited (t002–t004).
- **Decisions and docs.** ADR 0008 and ADR 019 carry the 2026-10-18 amendments (t001; the `mergePullRequest` rename is noted in `7ce5ec802`). `docs/mcp.md` (with the rename table), `docs/api-parity.md`, the prompts, the QA skill, both READMEs, and `backend-v2/AGENTS.md` name only the new tools (t006, t008).
- **Gates.** `tools/list` measures 96,458 bytes against a 96 KiB gate, and the tool count is 43 (t005).
- **Directories.** On 2026-10-18, with the deploy through `8d751b15b`, the OpenAI rescan has no "operations that are not individually exposed" finding, and Claude's Tools step lists all 43 tools with no flags (t007).
- **Follow-ups outside this milestone:** [w1/173](../../blocked/173.md) (`createLedger`/`updateLedger` need review, waiting on the user's decision) and [w1/171](../../blocked/171.md) (the website's MCP pages). The `mergePullRequest` rename (w1/172) reaches OpenAI with the next deploy.

## Source + Goal linkage

- **Source:** OpenAI Plugins dashboard scan of the Beancount.io draft, 2026-10-18. Seven tools (`editLedgerFiles`, `editEntrySource`, `manageBankImport`, `manageBankConnection`, `managePullRequests`, `manageLedgers`, `manageLedgerCollaborators`) received: "This tool appears to execute operations that are not individually exposed. Please expose each model-callable operation upfront as a separate tool with a clear description, input schema, and annotations." `manageLedgers` also received "This new tool definition needs further review before it can be published." Claude's review criteria point the same way: "Ideally, split write operations further by action type: create, update, and delete."
- **Goal linkage:** **A3: community and distribution** (primary). These findings are the remaining blocker between the draft and the ChatGPT app directory. A listing there and in Claude's directory is the owner's top adoption goal (2026-10-09). **A1** (secondary): granular tools carry accurate per-operation annotations, so hosts auto-approve reads and confirm only real destructive actions.
- **Expected outcome:** the ChatGPT submission passes automated checks, and both directories see precise per-operation tools. Signal: zero blocking findings on rescan, then directory acceptance.
- **Why now:** this is the last code-side blocker for the ChatGPT submission. It deliberately reverses ADR 0008 D3, which grouped tools to keep `tools/list` small, because directory acceptance outranks tool-count economy (owner decision 2026-10-09). The renamed tools break MCP clients that call the old names; the release note and docs cover that. Adoption surface is included because every connecting agent sees the new tool list.
