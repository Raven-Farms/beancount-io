# w23 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

## Inbox

- [003](./003.md) — archive names without a format, or an unknown commit SHA, report `SERVICE_UNAVAILABLE` (the SHA after a 90s hang)
- [004](./004.md) — `banks/{itemId}` looks the item up before authorizing (`BAD_USER_INPUT` vs. concealed `NOT_FOUND`) and ignores the path ledger
- [005](./005.md) — `readLedgerFiles` `totalLines` and write-preview diffs count a phantom line after the final newline
- [006](./006.md) — journal `directiveTypes` is case-sensitive and unvalidated; `["transaction"]` returns an empty success on REST, GraphQL and MCP
- [007](./007.md) — `updateEntrySource` summary prints the new hash as the old one
