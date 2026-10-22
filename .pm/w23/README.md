# w23 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

## Dropped

- ~~**046**~~ — social follower/following/starred lists answer an unknown user with an empty success — dropped 2026-10-21: documented behavior (`backend-cluster/backend-v2/docs/mcp.md`, social reads: "returns an empty page on upstream failure, so an empty result does not establish that the user has no followers or stars")

## Inbox

- [057](./057.md) — nested tool-argument objects still drop unknown keys: `readLedgerFiles` `startLine` returns the whole file; a misspelt `sourceAccount` imports against the default account
- [056](./056.md) — `renameLedgerFile` moves a file without rewriting its own relative includes: `include "x.bean"` in `d/inc.bean` resolves to `e/x.bean` after a move to `e/`
- [055](./055.md) — deleting an entry leaves the blank separator lines its insertion added: every add → delete cycle grows `main.bean`
- [054](./054.md) — file paths accept control characters, bidi overrides and Windows-invalid names (`\n`, `aux.bean`, `a:b`): committed files break `git clone` on Windows and can't be `include`d
- [053](./053.md) — `addLedgerEntries` writes numeric/date-looking string meta unquoted: `"00123"` reads back `123`, `"02134"` `2134` (hosted counterpart of CLI w5/128)
- [052](./052.md) — `updateLedgerFiles` small gaps: identical old/new makes an empty commit ("Committed 1 change(s)"); empty `old_string` "matches 47 times"; unknown key → "files.0: Invalid input"
- [051](./051.md) — `updateLedgerFiles` commits `new_string` through `String.replace`: `$&`/`$$`/`` $` ``/`$'` expand, so the commit differs from the literal dry-run preview
- [050](./050.md) — statement summaries silently drop balances not in the stated currency: `conversion=units` net worth 715.58 vs 117,458; unpriceable `conversion=EUR` still says `latest-price`
- [049](./049.md) — guided setup writes account names and the title raw: a `blank@1` account name injects directives; a title ending in `\` leaves `main.bean` unparseable
- [048](./048.md) — guided setup with a known opening builds a broken ledger: `Equity:OpeningBalances` opened twice in 6 of 8 presets; no validation despite ADR021
- [022](./blocked/022.md) — report rustledger BQL gaps upstream (`cost(sum(position))`, `neg`/`filter_currency`, `meta('lineno')`, `AT value`, `BALANCES FROM`) — **blocked:** filing in an external tracker needs the user's approval
- [026](./blocked/026.md) — streaming archive route for MCP OAuth clients over 8 MiB (option 1 from 023) — **blocked:** an ADR 0007 trust-boundary decision for the owner
