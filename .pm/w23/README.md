# w23 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

## Inbox

- [009](./009.md) — `isStarred` is readable only on GraphQL; REST and MCP `getLedger`/`metadata` omit it
- [010](./010.md) — `runBqlQuery` has no row cap; one `JOURNAL` returns 5.2 MB of text
- [011](./011.md) — one non-UTF-8 `.bean` anywhere in the repo, even unincluded, breaks every read with an unnamed `BAD_USER_INPUT`
- [012](./012.md) — BQL `cost(sum(position))` over mixed currencies returns one mislabelled amount (rustledger 0.24.0)
- [013](./013.md) — statement summaries add balances as floats (`netWorth: 906.5799999999999`)
