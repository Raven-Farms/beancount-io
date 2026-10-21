# w23 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

## Inbox

- [015](./015.md) — BQL position cells drop the lot date and label (`{197.06 USD}` vs `{197.06 USD, 2015-09-15}`)
- [016](./016.md) — hosted BQL rejects `neg(inventory)`, `filter_currency(position, …)`; `meta('lineno')` empty
- [017](./017.md) — concurrent file writes: the loser gets `SERVICE_UNAVAILABLE` instead of the promised retry/`CONFLICT`
- [018](./018.md) — `appendLedgerText` accepts `option`/`plugin`/`include` lines, silently reconfiguring the ledger
- [019](./019.md) — ledger search silently accepts `order=sideways`, `limit=0`, negative ids
- [020](./020.md) — BQL `BALANCES AT value` returns units; `BALANCES FROM <window>` fails "No matching lot" (rustledger 0.24.0)
- [021](./021.md) — OAuth grants unknown scopes verbatim (`ledger.superuser` lands in the signed token)
- [022](./blocked/022.md) — report rustledger's multi-currency `cost(sum(position))` collapse upstream — **blocked:** filing in an external tracker needs the user's approval
- [023](./023.md) — archives over 8 MiB unreachable for OAuth MCP clients: the documented fallback URL refuses the MCP token
- [024](./024.md) — bank-account tools look the account up before authorizing (`ledger.read` gets "Account not found" from admin tools)
- [025](./025.md) — adding/removing the ledger owner as a collaborator reports success but does nothing
