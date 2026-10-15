# w6 · m3 — Expose core ledger options consistently across API surfaces

**Worker:** worker1 **Goal:** Agents and API clients can read effective bookkeeping options without reconstructing defaults from source files. **Status:** done

**Severity:** minor. **Owner:** backend-v2. **Estimate:** 3–4 hours across seven tasks, including explicit operation coverage and cross-adapter validation.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Define and inventory the existing core-options read — **DONE** | 35m | — |
| t002 | Expose shared REST and MCP resource adapters — **DONE** | 55m | t001 |
| t003 | Verify effective options and failures across all surfaces — **DONE** | 35m | t002 |
| t004 | Adoption surface — **DONE** | 20m | t003 |
| t005 | Simplify — **DONE** | 15m | t004 |
| t006 | Test coverage — **DONE** | 35m | t004, t005 |
| t007 | Closeout — **DONE** | 10m | t006 |

## Live finding

Production `https://beancount.io`, 2026-10-14; local main `93bc513b`. MCP `beancount-mcp` 1.0.0, protocol `2025-11-25`; deployed SHA unavailable. Existing designated unpinned QA API key, scopes `ledger.read ledger.write ledger.admin`; only public synthetic `open_ledger/example` was read.

GraphQL, twice in fresh requests:

```graphql
query {
  getLedger(ledgerId: "open_ledger/example") {
    id
    options {
      title nameAssets nameEquity nameExpenses nameIncome nameLiabilities
      accountCurrentConversions accountCurrentEarnings
      renderCommas operatingCurrency
    }
  }
}
```

Both requests succeed with identical ten-field options, including title `Example Beancount file`, conversion/earnings account suffixes `Conversions:Current` / `Earnings:Current`, `renderCommas: true`, and `operatingCurrency: ["USD"]`.

REST `GET /api-gateway/v1/legacy/ledger-meta?ledgerId=open_ledger%2Fexample` succeeds, but its options contain only the five root-account names and operating currencies. It omits title, conversion/earnings account settings and comma rendering. The modern ledger metadata read contains repository metadata, not these options. The live public OpenAPI inventory has no core-options route; source inspection finds only the six-field legacy projection outside GraphQL.

The live `resources/templates/list` has 63 templates with no core-options resource. The 26 tools expose no equivalent read: `getLedgerContext` returns attributes, accounts, currencies, payees, years and files, with no options in its attributes object. In this fixture its nine used currencies are not equivalent to the one operating currency. Source inspection confirms neither the MCP resource registry nor the context aggregation calls the existing core-options workflow.

This is a missing structured capability under the repo's all-eligible-surfaces rule, not a request to promote another tool for tool-only hosts. A resource is appropriate. Guessing a URI and observing 404 is not the proof: the live inventories, actual payloads and source call sites establish the absence. Reading raw files and reconstructing defaults is not an equivalent API contract.

## Root cause and repair boundary

`LedgerQueryResolver.options` in `backend-cluster/backend-v2/src/features/ledger/api/resolvers/ledger-resolver.query.ts` calls `LedgerWorkflow.getLedgerOptions`. That workflow already reads the effective native options, applies the existing reports-read decision, and returns the ten camel-case fields. `getLegacyMetadata` intentionally projects six raw-name fields for older clients. The REST/MCP modern read fragments never expose the full workflow result.

Reuse `LedgerWorkflow.getLedgerOptions` for a modern discoverable REST read and an MCP resource, for example `/v1/ledgers/{owner}/{name}/options` and `beancount://{owner}/{name}/options`. Preserve the GraphQL nested field and the legacy metadata envelope/target fallback unchanged. Bind the capability explicitly in operation/parity coverage so removing an adapter is detected; the existing root-operation inventory alone did not reveal this nested-field gap. Do not regenerate or weaken the frozen historical baseline, invent an exception, expand credential policy, or hide missing adapters behind file/BQL workarounds. T001 must choose a coherent operation binding for the existing nested read without changing its semantics merely to satisfy a counter.

Scope is the ten core `LedgerOptions` fields only. Fava UI preferences, fiscal-calendar settings on the separate Fava-options field, mutations, a new hero read tool, and unrelated nested GraphQL field inventory are outside this milestone. Do not append more unbounded metadata to `getLedgerContext`; w6/013 separately repairs that tool's payee limit.

## Definition of done

The same effective core ledger options are discoverable and readable through REST, GraphQL and MCP with equivalent results, defaults and failures under existing policy. Tests use a fixture whose operating currency differs from posted currencies and whose option overrides differ from defaults. Legacy metadata and GraphQL behavior remain compatible. The new adapters delegate to the same existing workflow, with no reimplemented default parser. Operation coverage catches removal of either counterpart, existing parity debt stays zero, OpenAPI is generated and consistent, native backend checks pass, and customer documentation names the read.

## Source + Goal linkage

- **Source:** live functional MCP QA; ignored `.tmp/qa-2026-10-11/mcp-loop/`: `graphql-oct14-ledger-options.json`, `graphql-oct14-ledger-options-repeat.json`, `rest-oct14-legacy-ledger-meta.json`, `rest-oct14-live-openapi.json`, `oct14-current-resource-templates.json`, `oct14-context-limit-500.json`, `oct14-tools.json`, and the matching modern metadata controls.
- **Goal linkage:** A1 — Agent-native accounting. Consumers can discover the effective operating currency and configured account roots without parsing files or assuming USD/default names.
- **Expected outcome:** a client choosing REST or MCP can read the same effective bookkeeping configuration available through GraphQL.
- **Why now:** the gap is live with the same ordinary QA credential, and current main already has the protected producer needed for a bounded adapter repair.

## Dedupe and limits

All board states were searched for core ledger options, `Ledger.options`, `getLedgerOptions`, REST/MCP configuration parity and the original context-tool acceptance. Completed w2/m27 initially mentioned options in its hero-read task, but the current context contract and implementation contain only vocabulary; expanding that tool is not the requested repair. The legacy metadata MCP exclusion remains legitimate for that compatibility operation, but it does not exempt the modern core-options capability. No core-options structural exception was found in ADR 008 or the current parity contract. The earlier source-only context-options candidate was not filed because tool-only inconvenience alone was insufficient; this finding instead establishes the absent protocol counterparts to the actual GraphQL capability.

Unverified: all other nested GraphQL fields, custom-option live fixtures, final route names/operation binding, a deployed repair, and repository-URL reachability. Metadata URLs themselves matched MCP/REST and had coherent public repository paths; no clone/export workflow was performed. No ledger/account data changed; no product fix implemented.
