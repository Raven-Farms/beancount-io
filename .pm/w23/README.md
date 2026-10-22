# w23 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

## Dropped

- ~~**046**~~ — social follower/following/starred lists answer an unknown user with an empty success — dropped 2026-10-21: documented behavior (`backend-cluster/backend-v2/docs/mcp.md`, social reads: "returns an empty page on upstream failure, so an empty result does not establish that the user has no followers or stars")

## Inbox

- [056](./056.md) — `renameLedgerFile` moves a file without rewriting its own relative includes: `include "x.bean"` in `d/inc.bean` resolves to `e/x.bean` after a move to `e/`
- [055](./055.md) — deleting an entry leaves the blank separator lines its insertion added: every add → delete cycle grows `main.bean`
- [054](./054.md) — file paths accept control characters, bidi overrides and Windows-invalid names (`\n`, `aux.bean`, `a:b`): committed files break `git clone` on Windows and can't be `include`d
- [053](./053.md) — `addLedgerEntries` writes numeric/date-looking string meta unquoted: `"00123"` reads back `123`, `"02134"` `2134` (hosted counterpart of CLI w5/128)
- [052](./052.md) — `updateLedgerFiles` small gaps: identical old/new makes an empty commit ("Committed 1 change(s)"); empty `old_string` "matches 47 times"; unknown key → "files.0: Invalid input"
- [051](./051.md) — `updateLedgerFiles` commits `new_string` through `String.replace`: `$&`/`$$`/`` $` ``/`$'` expand, so the commit differs from the literal dry-run preview
- [050](./050.md) — statement summaries silently drop balances not in the stated currency: `conversion=units` net worth 715.58 vs 117,458; unpriceable `conversion=EUR` still says `latest-price`
- [049](./049.md) — guided setup writes account names and the title raw: a `blank@1` account name injects directives; a title ending in `\` leaves `main.bean` unparseable
- [048](./048.md) — guided setup with a known opening builds a broken ledger: `Equity:OpeningBalances` opened twice in 6 of 8 presets; no validation despite ADR021
- [047](./047.md) — every ledger-service 404 reads "Ledger resource not found": stale entry hashes and unknown branches tell the agent its ledger is missing
- [045](./045.md) — activity feed accepts negative/fractional `offset`/`limit`: `limit=-1` returns 97 of 98 items, `offset=-3` the oldest two (REST, GraphQL, MCP)
- [044](./044.md) — `plaintext-journal` has no limit/paging: 276 KB in one read on `open_ledger/example`, unbounded for premium (010 class)
- [043](./043.md) — structured amount `.5` passes the decimal check but is written raw: opaque "parse errors in main.bean"
- [042](./042.md) — entry-source write tools hard-code `wrote: []` (documented as files touched); `deleteEntrySources` echoes duplicate hashes
- [041](./041.md) — `appendLedgerText` moves entries away from their `pushtag`/`poptag` (date insertion): the tag is silently dropped, or a dangling push breaks the file
- [040](./040.md) — DCR accepts a `web` client with a plain `http://` non-loopback redirect URI (MCP auth spec requires https or loopback)
- [039](./039.md) — MCP whole-file `content` replace and delete take no base `sha` (REST requires one): a read-modify-write silently drops commits made in between
- [038](./038.md) — `commits` silently caps `limit` at 50 (1000 → 50), undeclared on every surface
- [037](./037.md) — over-long ledger description refused with raw "[Description]: MaxSize"; no surface declares the limit
- [036](./036.md) — `updateEntrySource` accepts `option`/`include`/several directives as one entry's replacement (018 class on the source-slice path)
- [035](./035.md) — `appendLedgerText` `path` to a file outside the include closure (even `notes.txt`) succeeds with "No new bean-check errors"; the entry is never loaded
- [034](./034.md) — backend-v2 `diffBeanCheckErrors` keys on file:line, so an existing error moved by an insertion is "new" and `appendLedgerText` refuses valid text
- [033](./033.md) — `addLedgerEntries` renders tags, links, flags, accounts, currencies and meta keys raw: one entry with a newline in a tag smuggles extra directives
- [032](./032.md) — stale `sha` and create-over-existing answer `400 BAD_USER_INPUT` instead of the documented `409 CONFLICT` (Gitea 422 bypasses the conflict mapping)
- [031](./031.md) — deleting `main.bean` commits with "No new bean-check errors" (post-write check fails open) and breaks every read; its dry run says `SERVICE_UNAVAILABLE`
- [022](./blocked/022.md) — report rustledger BQL gaps upstream (`cost(sum(position))`, `neg`/`filter_currency`, `meta('lineno')`, `AT value`, `BALANCES FROM`) — **blocked:** filing in an external tracker needs the user's approval
- [026](./blocked/026.md) — streaming archive route for MCP OAuth clients over 8 MiB (option 1 from 023) — **blocked:** an ADR 0007 trust-boundary decision for the owner
