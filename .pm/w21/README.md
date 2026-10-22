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
- [453](./blocked/453.md) — addEntries/bulkEntries have no idempotency key: a retry after a lost response can duplicate the entry (split from 351) — **blocked:** needs an owner-approved contract (field, bounds, retention) across REST/GraphQL/MCP and a backend-v2 deploy
- [509](./509.md) — New Transaction's payee suggestions list "Whole Foods" and "Whole  Foods" separately; Merchants merges them
- [510](./510.md) — A resumed Create Ledger draft demands an opening balance "again" that was never entered (w21/500 false positive)
- [511](./511.md) — Create Ledger: Create works while the preview loads, looks enabled after it fails, and the failure isn't announced (w21/478)
- [512](./512.md) — Notifications' "Show older" hides one page early after a foreground refetch (w21/498 regression)
- [513](./513.md) — Home's Recent Transactions misses its offline cache on a later day (daily window key; w21/471 regression)
- [514](./514.md) — Add Budget refuses a decimal comma ("49,99") that New Transaction accepts
- [515](./515.md) — Reports' chart and Cash flow say "No cash flow in this range" above Expenses' "Not in total: 420.00 EUR" (sibling of w21/493)
- [516](./516.md) — An account with only a future posting shows "$0.00 · Not enough data" while its Accounts row says −$20,000.00 (w21/491)
- [517](./517.md) — A units account chart still runs past today: 1M reads "+3 VOO" from next month's buy (w21/491 incomplete)
- [518](./518.md) — New Transaction books a plain first-row amount as money *into* the bank (Checking +4.50, Groceries −4.50); needs a product call
- [519](./519.md) — Payee suggestions, usual accounts and merchants miss a Smart Punctuation apostrophe ("Trader Joe’s") (sibling of w21/401)
- [520](./520.md) — New Transaction writes USD into a ledger without `operating_currency` (missed by w21/415 and w21/395)
- [508](./blocked/508.md) — Mobile guesses that an entry is a plugin copy from its first line; read the ledger's `generated_from` instead (split from 443) — **blocked:** production's GraphQL schema lacks `generated_from` until the ledger service and backend-v2 deploy; mobile's client is generated from it
- [315](./blocked/315.md) — In-app commits signed with Gitea username and real email (no full_name, no noreply) — **blocked:** needs the owner's noreply-address and published-history decisions, and a production backfill of existing Gitea users that can't be verified here
