# w0 · m5 — Directive counting runs on the worker pool, not the request thread

**Worker:** worker1 **Goal:** the ledger service's directive-limit precheck and `GET …/directive-count` parse on the rustledger worker pool, under its queue bound and timeout, and reuse the current count for an unchanged commit, so one large ledger's writes no longer stall requests for every other ledger **Status:** todo

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | Worker-pool `directive-count` task | 45m | — |
| t002 | Route both directive counts through it, and reuse the current count per commit | 45m | t001 |
| t003 | Inventory the remaining request-thread `Ledger.fromFiles` calls | 20m | t002 |
| t004 | Simplify | 15m | t003 |
| t005 | Test coverage | 30m | t003, t004 |
| t006 | Closeout | 10m | t005 |

## Definition of done

- `countMap` in `backend-cluster/ledger/src/core/directive-limit.ts` makes no `Ledger.fromFiles` call on the main thread outside Jest. Both the write precheck (`checkDirectiveLimitForFileChanges`) and `countDirectivesForRepo` go through the worker pool.
- A write to a ledger whose current commit was counted already parses only the projected map, not the current one again.
- With a maximum-size ledger's precheck in flight, `GET /healthz` and a small ledger's read answer without waiting for it (measured, with the numbers in the closeout).
- Queue-full and timeout outcomes keep today's documented fail-open behavior and are logged; a test pins it.
- Ledger typecheck, lint and tests pass, and the real-WASM worker verifier passes.

## Source + Goal linkage

- **Source:** security review of `main` (2026-10-18). `countMap` (`core/directive-limit.ts:36-39`) calls `withLedger` → `mod.Ledger.fromFiles` synchronously (`foundation/rustledger/engine.ts:120-132`), twice per checked write (`directive-limit.ts:129,139`), on file maps of up to 32 MiB (`file-map-loader.ts:41-43`). The engine's own comment puts a parse at ~100ms+/MB (`engine.ts:483-484`). Normal parsing goes through the worker pool, whose contract is that synchronous WASM never runs on the API event loop (`rustledger-worker-pool.ts:85-88`); this path breaks that contract. The service runs as one process.
- **Goal linkage:** **A1 — Agent-native accounting.** Agents write through MCP and REST in bursts; every tenant's writes and reads should stay responsive while one large ledger is being counted.
- **Expected outcome:** a large free-tier ledger's writes cost worker time, not shared request-thread time; health checks and other ledgers are unaffected.
- **Why now:** it is the availability fix with the widest blast radius from that review, and [m6](../m6/README.md) adds the same count to more write paths, so this lands first.
- **Adoption surface:** omitted. Internal execution change with no user- or agent-facing contract change.
