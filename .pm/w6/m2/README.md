# w6 · m2 — Preserve BQL expression types across projection aliases

**Worker:** worker1 **Goal:** Agents can trust query column types without interpreting identifiers as money or dates. **Status:** todo

**Severity:** minor. **Owner:** ledger, with backend-v2 adapter validation. **Estimate:** 3–4 hours across seven tasks; the current engine result has no cursor schema, so a general repair needs a type-provenance design rather than another alias allowlist.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Establish type provenance at the engine boundary | 45m | — |
| t002 | Preserve expression types in shell projections | 60m | t001 |
| t003 | Verify all eligible API adapters preserve corrected types | 25m | t002 |
| t004 | Adoption surface | 20m | t003 |
| t005 | Simplify | 15m | t004 |
| t006 | Test coverage | 35m | t004, t005 |
| t007 | Closeout | 10m | t006 |

## Live finding

Production `https://beancount.io`, 2026-10-14; local main `f2b01a4f`. MCP `beancount-mcp` 1.0.0, protocol `2025-11-25`; deployed SHA unavailable. Existing designated unpinned QA API key, scopes `ledger.read ledger.write ledger.admin`. Only public synthetic `open_ledger/example` was read.

Call `runBqlQueryStructured` with the ledger above and each query:

| Query | Actual dtype | Actual cell |
| --- | --- | --- |
| `SELECT '00123' AS reference LIMIT 1` | `Decimal` | `"00123"` |
| `SELECT '00123' AS account LIMIT 1` | `str` | `"00123"` |
| `SELECT '2025-01-01' AS reference LIMIT 1` | `date` | `"2025-01-01"` |
| `SELECT 'hello' AS reference LIMIT 1` | `str` | `"hello"` |

Every call succeeds. The first query repeated fresh produces the same result. REST `POST /api-gateway/v1/ledgers/open_ledger/example/query` with `{query: <same query>}` has the identical table for all four controls. GraphQL `queryShell(ledgerId: "open_ledger/example", query: "SELECT '00123' AS reference LIMIT 1")` also declares `Decimal` and returns the same string without errors.

These expressions are string literals: the live control `SELECT length('00123') AS chars, '00123' = 123 AS numeric_equal, '00123' = '00123' AS text_equal LIMIT 1` returns `[5, false, true]` with types int/bool/bool. An output label changes metadata for the same value and expression. The row text and leading zeros are preserved; actual numeric coercion by an agent or UI was not measured and is not claimed.

Helper pattern: `node .agents/skills/qa-shared/scripts/qa-mcp.mjs --credentials-file .env call runBqlQueryStructured '{"ledger":"open_ledger/example","query":"SELECT ..."}'`.

## Root cause and repair boundary

`backend-cluster/ledger/src/features/ledger/service/ledger-shell-mappers.ts`, `classifyColumnDtype`, classifies date-looking strings as dates and numeric-looking strings as Decimal, except numeric strings whose output name belongs to `STRING_COLUMNS`. A renamed column loses that exception. `LedgerShellService.queryShell` supplies only the resulting column names and cells to this mapper. The installed engine's `QueryResult` declaration contains columns, rows and errors, without cursor types; therefore this is an adapter inference problem, not evidence that the engine evaluates string literals as numbers.

Repair type provenance at the shared ledger query boundary. Do not fix only the word `reference`, expand the canonical-name allowlist indefinitely, treat all decimal strings as ordinary text, rewrite values, or introduce a second BQL parser. Evaluate supported engine metadata or a narrow existing expression-provenance facility first. Keep any engine work upstream and public, respect GPL containment, and do not vendor engine bytes. Adding dependencies still requires the repository's ordinary user approval. If a correct producer contract requires an unavailable upstream change, record that exact dependency and unblock condition with `/pm block` rather than inventing a cursor schema from result values.

Preserve existing decimal precision, Inventory/Amount/Position formatting, null-to-blank compatibility, text values and canonical row counts. REST, GraphQL and MCP must consume the same corrected producer metadata; do not add per-protocol type guesses or parity exemptions. This milestone does not promise to recover every empty-result expression type by heuristics; t001 must explicitly resolve the no-row and alias cases using the chosen producer contract.

## Definition of done

The three string-literal probes declare `str` independently of aliases. Ordinary string, Decimal, date, boolean and integer expressions retain their actual types, including aliases and null-first rows. Empty-result type behavior follows an explicit producer contract instead of an output-name accident. Existing values, leading zeros, precision, inventory shapes, null rendering and row counts stay intact. Real adapter checks demonstrate the same metadata through REST, GraphQL and MCP. Documentation describes supported type metadata and any genuine engine limitations; native owning-package checks and the zero-debt parity gate pass.

## Source + Goal linkage

- **Source:** live functional MCP QA; sanitized artifacts in ignored `.tmp/qa-2026-10-11/mcp-loop/`: `oct14-bql-alias-{leading-zero-label,leading-zero-account,date-label,string-label,leading-zero-repeat,string-semantics}.json`, their available REST controls, and `graphql-oct14-alias-type.json`.
- **Goal linkage:** A1 — Agent-native accounting. Type metadata should distinguish a zero-prefixed reference from a decimal amount without relying on its display name.
- **Expected outcome:** tool and API consumers can interpret typed query output consistently when projections are renamed.
- **Why now:** this is reproduced in current production on all three eligible protocols, independently of the already-fixed MCP row-count issue.

## Dedupe and limits

Searched all board states for dtype inference, numeric strings, aliased types, leading-zero query values and `ledger-shell-mappers`. Completed w3/m37 repairs dashboard rendering of correctly typed Inventory/Amount cells; w6/done/m1 repairs canonical row counts. Neither repairs expression typing. The mapper history still contains this inference in current main; no overlapping repair was found. Null-to-empty-string serialization is explicitly preserved compatibility and is not this finding.

Unverified: complete type behavior for arbitrary expressions or zero-row aliases, real downstream identifier coercion, the available upstream metadata solution, and a deployed fix. No ledger/account data changed; no product fix implemented.
