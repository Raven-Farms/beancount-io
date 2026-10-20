# w3 · m53 — Ledger creation: setup specification, catalog, and builder across hosted surfaces and `bea init`

**Worker:** worker3 **Goal:** one versioned setup specification and catalog turn into the same ledger files on every hosted surface and in local `bea init`, so a first ledger fits its owner's life and currency instead of the USD Starter. **Status:** todo (t001–t002 done)

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Freeze the versioned catalog and conformance fixtures — **DONE** | 90m | — |
| t002 | Build the backend pure builder and wire hosted creation to it — **DONE** | 90m | t001 |
| t003 | Add setup, idempotent create, and preview to REST, GraphQL, and MCP | 90m | t002 |
| t004 | Consume the same catalog in `bea init` and hosted CLI create | 60m | t001, t003 |
| t005 | Run cross-engine conformance for every listed preset | 45m | t002, t004 |
| t006 | Adoption surface | 30m | t005 |
| t007 | Simplify | 20m | t006 |
| t008 | Test coverage | 45m | t006 |
| t009 | Closeout | 10m | t007, t008 |

## Definition of done

- Creating with `personal@1`, a non-USD operating currency, and one `known` opening balance yields the same accounts, opening transaction on the day before `historyStart`, and balance assertion on `historyStart` via REST, GraphQL, MCP, hosted CLI, and local `bea init`.
- `unknown`, `zero`, and `known` opening states stay distinct; `unknown` writes no posting and never reads as zero.
- A repeated `requestId` creates exactly one ledger on every surface that accepts it.
- `template: SAMPLE` combined with a `setup` object, an unknown preset, an unsupported currency, or an impossible date is refused identically on every surface and creates nothing.
- Omitting `setup` behaves exactly as creation does today, including the USD Starter and private signup provisioning.
- Every listed preset passes the conformance fixtures on both engines (hosted builder and Python CLI) before it is listed.

## Source + Goal linkage

- **Source:** `/pm-brainstorm w3` 2026-10-20 candidate 1, from [PRFAQ001](../../../docs/prfaqs/PRFAQ001-ledger-creation.md) (scope approved; everything except private signup creation and the empty Starter is unimplemented) and [ADR021](../../../docs/adrs/ADR021-backend-v2-ledger-creation-experience.md) (Proposed).
- **Goal linkage:** A2 — Frictionless onboarding: a newcomer, human or agent, goes from zero to a working ledger in minutes.
- **Expected outcome:** a new user or agent creates a ledger matching their purpose and currency without typing Beancount or accepting a 1970 USD chart. Signals: time-to-first-ledger, share of new ledgers still on the default Starter chart after 7 days.
- **Why now:** w3 is the only queue with capacity (all other open work is blocked), and m54's staged dashboard/mobile flow cannot start until this contract exists. Adoption surface is included (t006) because this milestone adds API fields, CLI flags, and a public catalog.
