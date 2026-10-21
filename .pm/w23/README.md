# w23 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

## Inbox

- [007](./007.md) — `updateEntrySource` summary prints the new hash as the old one
- [008](./008.md) — a failed `createLedger` leaves its `requestId` stuck "in progress" for 24h; the retry answers `CONFLICT` with an entry-edit hint
- [009](./009.md) — `isStarred` is readable only on GraphQL; REST and MCP `getLedger`/`metadata` omit it
- [010](./010.md) — `runBqlQuery` has no row cap; one `JOURNAL` returns 5.2 MB of text
