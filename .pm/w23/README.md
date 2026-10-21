# w23 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

## Inbox

- [029](./029.md) — `renameLedgerFile` matches include lines literally: misses relative includes in subdirectories, falsely refuses, and with `updateIncludes` rewrites an unrelated include to a missing file
- [028](./028.md) — two `old_string` edits to one file in one `updateLedgerFiles` call: preview shows both, commit silently keeps only the last
- [027](./027.md) — a `.git` path segment reads as `SERVICE_UNAVAILABLE` on every surface and passes write dry runs
- [022](./blocked/022.md) — report rustledger BQL gaps upstream (`cost(sum(position))`, `neg`/`filter_currency`, `meta('lineno')`, `AT value`, `BALANCES FROM`) — **blocked:** filing in an external tracker needs the user's approval
- [026](./blocked/026.md) — streaming archive route for MCP OAuth clients over 8 MiB (option 1 from 023) — **blocked:** an ADR 0007 trust-boundary decision for the owner
