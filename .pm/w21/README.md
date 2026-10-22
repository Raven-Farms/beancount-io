# w21 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [x] **m1** — [Entry edits and deletes refuse changes that would break the ledger](./done/m1/README.md) (7 tasks) ← from mobile QA 2026-10-20

## Dropped

- ~~**052**~~ — Drawer header words split mid-word at the largest text size — dropped 2026-10-21: reproduces only at AX5; at AX2 (`accessibility-large`) the header renders whole words (`.pm/DO_NOT_DO.md`, AX2 ceiling).

## Inbox

- [064](./blocked/064.md) — A token refresh whose response is lost signs the user out on the next refresh (rotated token replayed → grant revoked) — **blocked:** needs an owner decision (ADR) on a refresh-token reuse grace window
- [065](./blocked/065.md) — One early-year entry (e.g. 0050) makes the balance sheet 23,718 monthly points (3 MB) and the app stalls — **blocked:** needs an approach decision (per-pill fetch vs server downsample) and a simulator profile of the stall
- [180](./blocked/180.md) — Budget actuals use raw prefix match (`Transport` counts `Transportation`), unlike Reports — **blocked:** needs an owner decision between component matching on the server (a Fava break) and a per-account breakdown for the client
- [201](./blocked/201.md) — Missing file: GraphQL returns null, REST/MCP NOT_FOUND; directory path differs too — **blocked:** needs an owner decision on the file-read contract (null vs NOT_FOUND), which the dashboard's README reads and shipped mobile builds rely on
- [206](./blocked/206.md) — Refund/return receipts are always prefilled as a purchase — **blocked:** needs an owner-approved AI-quota evaluation and a parse-contract decision (`isRefund` vs signed amount)
- [210](./blocked/210.md) — Holdings sheet labels a user-typed price "Live price" and applies the feed's staleness rule — **blocked:** needs an owner decision on exposing the feed's effective price dates (cross-package contract) and a deploy before mobile can read it
- [228](./blocked/228.md) — New Transaction stamps the first operating currency on every posting; no currency or price control — **blocked:** needs account-constraint currencies on the client, a price path (legacy field or typed mutation, deploy first) and an owner-approved form design
- [304](./blocked/304.md) — Budgets on Liabilities/Assets get favourability backwards (owner decision) — **blocked:** needs an owner decision between deriving direction from the account root and limiting the picker to Income and Expenses, which reverses w1/023's "every root" rule
- [424](./blocked/424.md) — Mobile does not show the ledger service's fix hints (split from 311) — **blocked:** production's GraphQL schema lacks `code`/`hint` until backend-v2 deploys; mobile's client is generated from it
- [453](./blocked/453.md) — addEntries/bulkEntries have no idempotency key: a retry after a lost response can duplicate the entry (split from 351) — **blocked:** needs an owner-approved contract (field, bounds, retention) across REST/GraphQL/MCP and a backend-v2 deploy
- [496](./blocked/496.md) — Mobile guesses that an entry is a plugin copy from its first line; read the ledger's `generated_from` instead (split from 443) — **blocked:** production's GraphQL schema lacks `generated_from` until the ledger service and backend-v2 deploy; mobile's client is generated from it
- [488](./488.md) — Invite Friends read twice by VoiceOver; summary never spoken
- [489](./489.md) — Guest journal link drops its filters (344/345 gap)
- [490](./490.md) — Guest links to Accounts/Files still hit sign-in (345 follow-up)
- [491](./491.md) — Regression (420): account chart runs past today; future entry moves 1M
- [492](./492.md) — Regression (423): Reports shows $0.00 · 0% net-zero category again
- [493](./493.md) — Regression (418): 'No spending yet' above a Not in total note
- [494](./494.md) — Regression (418): Spending caption drops refund sign
- [495](./495.md) — 427 getLedgerFile guard never fires; AGENTS.md dangling ref (413)
- [496](./496.md) — Reports chart draws all-zero range as 2pt bars on $0–$1 axis
- [497](./497.md) — Bar-chart month labels lack year: Budget 1Y has two OCT
- [498](./498.md) — Show older never hides at a multiple of 30 commits (431 regression)
- [499](./499.md) — Home charts show duplicate title under the tab (441 regression)
- [500](./500.md) — 435 incomplete: resumed draft still creates without balance
- [501](./501.md) — Stored draft fingerprint reveals opening amount (434 vs 053)
- [502](./502.md) — Create retry across midnight mints new requestId (436+434)
- [503](./503.md) — 454's sign-in failure still silent on iOS (role alert is no-op)
- [504](./504.md) — First series copy with escaped quote still offers Delete (443 gap)
- [505](./505.md) — Multi-line/pipe-header entries lose Edit and Delete (443 false positive)
- [506](./506.md) — Money flow pads BND/AMD/NOK share counts as money (445 regression)
- [507](./507.md) — Refused edit shows banner and toast with different citations (369 follow-up)
- [315](./blocked/315.md) — In-app commits signed with Gitea username and real email (no full_name, no noreply) — **blocked:** needs the owner's noreply-address and published-history decisions, and a production backfill of existing Gitea users that can't be verified here
