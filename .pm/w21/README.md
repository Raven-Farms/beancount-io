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
- [454](./454.md) — Welcome keeps old server's sign-in error; not announced
- [455](./455.md) — Budget ALL shows $0 / Below target while current period loads or fails
- [456](./456.md) — Budget chart y-axis floored at 1 hides BTC bars
- [457](./457.md) — Budget chart summary says missed income is over target; no years
- [458](./458.md) — One shifted twice-a-month payment turns it biweekly
- [459](./459.md) — A skipped month drops a monthly bill's day anchor
- [460](./460.md) — Internal double spaces split one merchant in two
- [461](./461.md) — Recurring paycheck's typical amount is unsigned
- [462](./462.md) — Deleting the last posting overwrites the typed amount above it
- [463](./463.md) — Locale-formatted amounts (1.234,56, 1 234,56, U+2212) refused
- [464](./464.md) — Quote hint glued to refusal without punctuation (369 follow-up)
- [465](./465.md) — Refresh leaves 'Couldn't load more' and stops paging (353 follow-up)
- [466](./466.md) — Transactions search literal on NFC/NFD and spacing
- [467](./467.md) — Android search field has no clear button
- [468](./468.md) — Save to a deleted file answers SERVICE_UNAVAILABLE, not NOT_FOUND (378 server half)
- [469](./469.md) — Regression (364): Home budget panel shows $0.00 actual for monthly budgets
- [470](./470.md) — Pull to refresh skips Spending's to-today read (337 follow-up)
- [471](./471.md) — Upcoming entries can fill all of Recent Transactions
- [472](./472.md) — 388 not fixed natively: detail lacks new metadata after save
- [473](./473.md) — 'Show N more lines' ignores plurals (379 follow-up)
- [474](./474.md) — Editor tells a FORBIDDEN save to try again (378 follow-up)
- [475](./475.md) — Dashboard budget chart takes an income target's direction from today's amount; zeroed income runs on expense rules (394 dashboard half)
- [476](./476.md) — Custom/budget hash ignores account and amount; stale delete removes another budget
- [477](./477.md) — Create Ledger Review shows MyBook but creates mybook; no visibility line
- [478](./478.md) — Create Ledger preview failure shows raw English, no Retry
- [479](./479.md) — Create Ledger errors silent to VoiceOver (354 sibling)
- [480](./480.md) — Budget pages past 500 never re-read on refresh (397 follow-up)
- [481](./481.md) — Load errors/empty states/captions in black60 (1.78:1 light)
- [482](./482.md) — Budget status badges fail contrast (2.22:1 dark)
- [483](./483.md) — Light editor strings/currencies below 4.5:1
- [484](./484.md) — Profile, server settings, budget delete errors not announced (354 sibling)
- [485](./485.md) — Files Up and budget Delete targets under 44pt
- [486](./486.md) — Regression (398): closed parent with open children budgets $0, leaves Home
- [487](./487.md) — Recent changes and commit detail show no time; same-day commits indistinguishable
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
- [315](./blocked/315.md) — In-app commits signed with Gitea username and real email (no full_name, no noreply) — **blocked:** needs the owner's noreply-address and published-history decisions, and a production backfill of existing Gitea users that can't be verified here
