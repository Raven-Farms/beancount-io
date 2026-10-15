# w6 · m4 — Complete empty-narration transaction lookups across APIs

**Worker:** worker1 **Goal:** An agent can retrieve the latest transaction whose narration is the valid empty string through REST, GraphQL and MCP. **Status:** todo (t001 done)

**Severity:** minor. **Owners:** ledger producer and backend-v2 adapters, in their existing package boundaries. **Estimate:** about 2 hours across six tasks; normalization alone leaves the MCP input unaddressable and GraphQL still discards an empty result field.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Match and return canonical empty narrations at the producer — **DONE** | 25m | — |
| t002 | Complete MCP addressing and GraphQL field preservation | 40m | t001 |
| t003 | Adoption surface | 15m | t002 |
| t004 | Simplify | 10m | t003 |
| t005 | Test coverage | 30m | t003, t004 |
| t006 | Closeout | 10m | t005 |

## Live reproduction and expected result

Production `https://beancount.io`, 2026-10-15; local main `c616abcb`. MCP `beancount-mcp` 1.0.0, protocol `2025-11-25`; deployed SHA unavailable. Designated unpinned QA API key with `ledger.read ledger.write ledger.admin`; only public synthetic `open_ledger/example` was read. No ledger mutation or product fix was performed.

`GET /api-gateway/v1/ledgers/open_ledger/example/narration-transactions?narration=` returns no transaction (HTTP 204), including a fresh repeat. The empty expansion of the published MCP template, `beancount://open_ledger/example/narration-transactions/`, returns JSON-RPC -32002/NOT_FOUND twice. GraphQL `getLedgerNarrationTransactions(ledgerId:"open_ledger/example", narration:"") { date payee narration postings { account amount commodity } }` produces data:null/INTERNAL_SERVER_ERROR.

This time a matching transaction **does exist**. BQL `SELECT date, payee, narration, account, number WHERE narration = '' ORDER BY date DESC LIMIT 2` returns the two postings of the August-23-2017 Wine-Tarner Cable payment. Canonical hash `b71994c29b0e3be4a2ac5fb2e88126e9` resolves through live getEntryContext to source line 819 in main.bean:

```beancount
2017-08-23 * "Wine-Tarner Cable" ""
  Assets:US:BofA:Checking -80.08 USD
  Expenses:Home:Internet   80.08 USD
```

The expected latest-match result has that date, payee, both postings and **narration:""**. The complete captured 1,044-transaction journal has 173 empty-narration transactions; a live BQL count finds 346 matching postings and zero NULL narrations. Do not equate that API/BQL empty string with an absent native JSON field when searching.

Working controls: `Buying groceries` selects the September-6-2017 Farmer Fresh entry from 73 matches. `Investing 60% of cash in RGAGX` selects the later compiled-source entry among two on August 14 (1.843 RGAGX, not the earlier 3.685). Both MCP and REST agree. The earlier `Workshop facilitation + 8.5% sales tax` lookup also round-trips percent-encoded punctuation correctly.

## Causes and correction boundaries

- **Producer:** `backend-cluster/ledger/src/features/ledger/service/ledger-data-service.ts:346–379` compares `t.narration === params.narration` on raw DirectiveJson and emits `directive.narration ?? null`. The installed WASM 0.24.0 omits the narration property for the valid explicit-empty fixture above. A real in-memory `Ledger.fromFiles(...).expandPads()` control is valid with no errors and no narration property. The same fixture parsed by Beancount has narration equal to a string `""`. The existing journal serializer already documents and implements the canonical rule: narration is always a string, using `directive.narration ?? ""`.
- **MCP input:** the sole advertised resource puts narration in a required path segment, and the SDK path matcher does not match its empty expansion. REST and GraphQL string arguments accept empty strings. Provide an explicit empty-capable query-parameter form for this existing read, preserving the published nonempty path form. Reuse the same read/service and strict query handling; do not introduce a generic resource bridge or a new tool.
- **GraphQL output:** both transaction-lookup result mappers in `ledger-data-resolver.query.ts` use `data.narration || undefined`, so even after producer repair they would turn a valid empty narration into null. Preserve its empty string without changing absent-payee semantics or unrelated resolver fields.

Normalize narration only according to its existing Beancount string contract; do not broadly collapse null and empty across payees, metadata or other fields. Keep latest-entry ordering and positive posting amounts, commodities and prices. The [official Fava lookup](https://github.com/beancount/fava/blob/main/src/fava/core/attributes.py) searches reversed transactions by exact narration, and its [JSON endpoint](https://github.com/beancount/fava/blob/main/src/fava/json_api.py) returns that entry when found. Those sources were inspected; a running upstream Fava server was not exercised. No engine fork, parser replacement, vendored upstream source or dependency addition is needed.

## Definition of done

The real fixture above resolves to the latest matching transaction through modern REST, GraphQL and an advertised MCP URI that can carry narration="". All return narration:"" and the correct two postings. Existing nonempty path URIs continue working; an agent can discover how to pass an explicit empty value without inventing an encoding. Same-day ordering controls and nonempty lookups remain correct. Genuine no-match values remain absent, rather than being substituted with the latest blank entry.

Regression coverage uses actual installed WASM output and actual adapter serialization/URI matching, not just a handcrafted directive with an already-present empty string. Native ledger and backend checks pass, including backend parity/OpenAPI gates. Test the deployed endpoint separately after release; source completion alone does not claim production verification.

## Dedupe and adjacent findings

Searched all board states for empty/blank narration, lookup normalization, lastTransaction and narration-transactions; targeted history retains the raw comparison and path template. Completed w2/010 corrected descriptions of latest-transaction reads, not empty lookup behavior. CLI Unicode normalization and intentionally empty mobile-entry fields have other producers and callers.

w6/019 and 020 concern a **genuinely unmatched** lookup returning a valid null that adapters turn into an error or empty HTTP body. Here the producer falsely says no match for an existing blank-narration entry, and MCP cannot address its input. Fixing null handling alone would still return no transaction here. Coordinate adapter tests with those items, but do not close them merely because this positive-empty case starts working.

Ignored evidence in `.tmp/qa-2026-10-11/mcp-loop/`: narration-lookup-empty MCP/REST and fresh repeats; `graphql-oct15-empty-narration.json`; `oct15-empty-narration-source-context.json`; `oct15-empty-narration-latest-postings.json`; narration-empty-string-count/null-count MCP/REST; `oct15-empty-narration-wasm-control.json` (fixture, installed version, valid expanded snapshot); `oct15-empty-narration-python-control.json`; positive repeated-narration MCP/REST files; complete large-example journal pages; ignored inspected Fava source snapshots. No public personal data, credentials or native engine bytes are committed. UI autocomplete and actual agent decisions remain unverified.

## Source + Goal linkage

- **Source:** live qa-find-bugs-mcp lookup journey and native serialization controls, 2026-10-15.
- **Goal linkage:** **A1 — Agent-native accounting:** preserve a valid accounting text value and expose the same lookup input/result through every eligible API.
- **Expected outcome:** a client requesting a blank-narration template gets the actual latest matching entry, with no parser workaround or invented URI encoding.
- **Why now:** existing nullable-lookup corrections (019/020) can otherwise make the transport appear successful while silently retaining the false no-match. The implementation spans producer normalization, MCP addressing and GraphQL preservation, so it needs coordinated tasks and adapter coverage.
- **Adoption surface:** included because MCP clients must discover the empty-capable URI and its explicit-input behavior in the published resource catalog/docs; preserve both Claude Code and Codex usability.
