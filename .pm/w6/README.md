# w6 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [x] **m3** — [Expose core ledger options consistently across API surfaces](./done/m3/README.md) (7 tasks; minor; backend-v2).

- [ ] **m2** — [Preserve BQL expression types across projection aliases](./blocked/m2/README.md) (7 tasks; minor; ledger with backend-v2 validation) — **blocked:** the engine query result has no column types; needs a published `@rustledger/wasm` release that exposes them

- [x] **m1** — Count canonical BQL rows in MCP text summaries (7 tasks) ← from [003](./done/003.md).

## Inbox


- [014](./014.md) — Distinguish BQL output rows from input postings in MCP text and schemas (minor; backend-v2; 30–45m).
- [015](./015.md) — Remove unsupported addLedgerEntries descriptions from served playbooks (minor; backend-v2; 20–35m).

- [016](./blocked/016.md) — Adopt corrected PRINT filtering and cost-preserving rendering (major; ledger; 45–60m after release) — **blocked:** awaiting a published WASM artifact containing upstream 3ad34e07.

- [017](./blocked/017.md) — Adopt upstream BQL date subtraction support (minor; ledger; 35–50m after release) — **blocked:** awaiting a published WASM artifact containing upstream 6972f5ed.

- [018](./blocked/018.md) — Adopt upstream MIN/MAX support for posting amounts (minor; ledger; 35–50m after release) — **blocked:** awaiting a published WASM artifact containing upstream 25fc6be5.
