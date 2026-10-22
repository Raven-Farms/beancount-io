# w23 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

## Dropped

- ~~**046**~~ — social follower/following/starred lists answer an unknown user with an empty success — dropped 2026-10-21: documented behavior (`backend-cluster/backend-v2/docs/mcp.md`, social reads: "returns an empty page on upstream failure, so an empty result does not establish that the user has no followers or stars")

## Inbox

- [067](./067.md) — a posting before its account's `open` is reported as "never opened" (engine wording), inviting a duplicate `open`
- [066](./066.md) — asset download URL reveals which numeric ledger IDs exist (pinned: `FORBIDDEN` vs `NOT_FOUND`; account-wide: two different not-found messages)
- [065](./blocked/065.md) — a ledger-pinned credential keeps the old name after a rename — **blocked:** owner picks repository-ID pins, canonical-name pins, or an accurate refusal (credential trust boundary)
- [059](./blocked/059.md) — every product-created ledger ships `auto_accounts`, so a misspelt account is silently opened — **blocked:** owner picks drop-plugin (which also limits AI categorization to existing accounts) vs report-new-accounts
- [022](./blocked/022.md) — report rustledger BQL gaps upstream (`cost(sum(position))`, `neg`/`filter_currency`, `meta('lineno')`, `AT value`, `BALANCES FROM`) — **blocked:** filing in an external tracker needs the user's approval
- [026](./blocked/026.md) — streaming archive route for MCP OAuth clients over 8 MiB (option 1 from 023) — **blocked:** an ADR 0007 trust-boundary decision for the owner
