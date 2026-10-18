# w6 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [x] **m7** — [Connect OpenClaw and Hermes Agent to the hosted MCP endpoint](./done/m7/README.md) (9 tasks; A1; backend-v2 fixtures and docs) ← user request 2026-10-16 to list Beancount.io on OpenClaw and Hermes Agent; ADR 019 D8

- [ ] **m6** — [Publish the eight ledger skills to ClawHub for OpenClaw and Hermes Agent](./blocked/m6/README.md) (13 tasks; A3; skills and CI) ← user request 2026-10-16 to list Beancount.io on OpenClaw and Hermes Agent — **blocked:** t001 needs the owner's decision on ClawHub's MIT-0 terms and publishing handle; t002–t004 shipped

- [x] **m5** — [Include current earnings in balance-sheet equity](./done/m5/README.md) (6 tasks; major; ledger with backend-v2 validation).

- [x] **m4** — [Complete empty-narration transaction lookups across APIs](./done/m4/README.md) (6 tasks; minor; ledger and backend-v2).

- [x] **m3** — [Expose core ledger options consistently across API surfaces](./done/m3/README.md) (7 tasks; minor; backend-v2).

- [ ] **m2** — [Preserve BQL expression types across projection aliases](./blocked/m2/README.md) (7 tasks; minor; ledger with backend-v2 validation) — **blocked:** the engine query result has no column types; needs a published `@rustledger/wasm` release that exposes them

- [x] **m1** — Count canonical BQL rows in MCP text summaries (7 tasks) ← from [003](./done/003.md).

## Inbox



- [016](./blocked/016.md) — Adopt corrected PRINT filtering and cost-preserving rendering (major; ledger; 45–60m after release) — **blocked:** awaiting a published WASM artifact containing upstream 3ad34e07.

- [017](./blocked/017.md) — Adopt upstream BQL date subtraction support (minor; ledger; 35–50m after release) — **blocked:** awaiting a published WASM artifact containing upstream 6972f5ed.

- [018](./blocked/018.md) — Adopt upstream MIN/MAX support for posting amounts (minor; ledger; 35–50m after release) — **blocked:** awaiting a published WASM artifact containing upstream 25fc6be5.



- [022](./blocked/022.md) — Adopt BQL JOURNAL date windows and opening summaries (major; ledger; 45–60m after release) — **blocked:** awaiting a published WASM artifact containing upstream 1324bc25.

- [023](./blocked/023.md) — Adopt correct FROM predicate evaluation in BQL (major; ledger; 45–60m after release) — **blocked:** awaiting a published WASM artifact containing upstream a2d984d6.

- [024](./blocked/024.md) — Adopt hidden ORDER BY keys in subqueries and table groups (minor; ledger; 45–60m after release) — **blocked:** awaiting a published WASM artifact containing upstream 05b8588b.

- [025](./blocked/025.md) — Adopt quoted BQL column resolution (major; ledger; 45–60m after release) — **blocked:** awaiting a published WASM artifact containing upstream 9d3bde86.

- [026](./blocked/026.md) — Restore authored BQL source locations (minor; ledger; 45–60m after upstream support) — **blocked:** needs a published source-aware WASM query binding, not a known local patch.

- [027](./blocked/027.md) — Preserve GETPRICE currency argument normalization (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published Beanquery-compatible WASM lookup.

- [028](./blocked/028.md) — Preserve negative SPLITCOMP component indices (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published signed-index WASM implementation.

- [029](./blocked/029.md) — Preserve Beanquery SUBST replacement and null semantics (minor; ledger; 35–50m after upstream support) — **blocked:** needs a compatible published WASM replacement/null implementation.


- [031](./blocked/031.md) — Adopt floor-based DATE_BIN arithmetic before the origin (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published native fixed-stride correction.

- [032](./blocked/032.md) — Preserve calendar DATE_BIN origins and boundaries (minor; ledger; 45–60m after upstream support) — **blocked:** needs a published native month/year boundary correction.

- [033](./blocked/033.md) — Preserve typed zero amounts from ONLY inventory extraction (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published native zero-preserving extraction.

- [034](./blocked/034.md) — Preserve FINDFIRST prefix and case matching (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published native regex-policy correction.

- [035](./blocked/035.md) — Adopt FILTER_CURRENCY Position overload (minor; ledger; 35–50m after upstream support) — **blocked:** needs a compatible published native overload.

- [036](./blocked/036.md) — Preserve BOOL string and tag-set truthiness in BQL (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published native string/set truthiness correction.

- [037](./blocked/037.md) — Adopt short-circuit BQL logical guards (minor; ledger; 45–60m after upstream support) — **blocked:** needs a published native lazy logical evaluator.

- [038](./blocked/038.md) — Preserve integer arithmetic before type-sensitive BQL operations (minor; ledger; 45–60m after upstream support) — **blocked:** needs a published native integer-preserving arithmetic path.
