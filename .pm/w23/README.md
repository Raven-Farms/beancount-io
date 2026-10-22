# w23 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

## Dropped

- ~~**046**~~ — social follower/following/starred lists answer an unknown user with an empty success — dropped 2026-10-21: documented behavior (`backend-cluster/backend-v2/docs/mcp.md`, social reads: "returns an empty page on upstream failure, so an empty result does not establish that the user has no followers or stars")

## Inbox

- [064](./064.md) — `createLedger`/`updateLedger` accept names the schema allows but the service rewrites (`x-` → `x`, `a--b` → `a-b`): the next call by the sent name is `NOT_FOUND`
- [063](./063.md) — `leaveLedger` by the owner answers `NOT_FOUND` "Ledger not found" instead of the documented "owners cannot leave" (w23/025 fixed set/remove only)
- [062](./062.md) — auto-routed writes (`transaction_file "txns/{year}.bean"`) create a new year file nothing includes: the entry is committed, invisible to every report, and the write says "No new bean-check errors"
- [061](./061.md) — after a ledger rename, `createLedger` with the old name says "Name already exists" (a host redirect, not a ledger); a pinned token's own `listLedgers` shows the new name but refuses it as outside its restriction
- [060](./060.md) — `addLedgerEntries`/`appendLedgerText` always return `entryHashes: []`: an agent can't verify or undo the entry it just wrote without guessing via `listLedgerEntries` (pairs with w5/942)
- [059](./059.md) — every product-created ledger (STARTER, signup default, guided setup) ships `auto_accounts`, so a misspelt account is silently opened and writes report "No new bean-check errors" — owner picks drop-plugin vs report-new-accounts
- [058](./058.md) — `insertReceiptTransaction` stores the receipt before validating the entry: a refused (e.g. `UNBALANCED`) insert still commits an orphan `documents/…` file under git storage, or an orphan permanent copy under S3
- [057](./057.md) — nested tool-argument objects still drop unknown keys: `readLedgerFiles` `startLine` returns the whole file; a misspelt `sourceAccount` imports against the default account
- [056](./056.md) — `renameLedgerFile` moves a file without rewriting its own relative includes: `include "x.bean"` in `d/inc.bean` resolves to `e/x.bean` after a move to `e/`
- [055](./055.md) — deleting an entry leaves the blank separator lines its insertion added: every add → delete cycle grows `main.bean`
- [054](./054.md) — file paths accept control characters, bidi overrides and Windows-invalid names (`\n`, `aux.bean`, `a:b`): committed files break `git clone` on Windows and can't be `include`d
- [022](./blocked/022.md) — report rustledger BQL gaps upstream (`cost(sum(position))`, `neg`/`filter_currency`, `meta('lineno')`, `AT value`, `BALANCES FROM`) — **blocked:** filing in an external tracker needs the user's approval
- [026](./blocked/026.md) — streaming archive route for MCP OAuth clients over 8 MiB (option 1 from 023) — **blocked:** an ADR 0007 trust-boundary decision for the owner
