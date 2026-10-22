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
- [425](./425.md) — Zero-decimal budgets show ¥1,016.13 (290 regression)
- [426](./426.md) — Single-commodity account detail lacks price note (291/279 follow-up)
- [427](./427.md) — Guest: per-entry NOT_FOUND blanks whole example (292 gap)
- [428](./428.md) — Line-less editor error rows read as "dimmed" (276 regression)
- [429](./429.md) — New File refuses Mr.Smith/2024.Q/budget.march (275 follow-up)
- [430](./430.md) — Gravatar caption says "Add a photo" on any load failure (289 follow-up)
- [431](./431.md) — Show older skips a page / vanishes after any write (313 regression)
- [432](./432.md) — Error text and Entry Context source not copyable
- [433](./433.md) — Entry Context location truncates the line number first
- [434](./434.md) — Resumed Create Ledger draft reuses requestId with changed request: generic failure 24h
- [435](./435.md) — Draft resumed on Review drops the opening balance silently
- [436](./436.md) — Cleared Books begin → server UTC date (051 regression path)
- [437](./437.md) — In-progress create reported as name conflict
- [438](./438.md) — Setup ValidationError args swapped: garbled messages
- [439](./439.md) — Chart VoiceOver stepping desyncs on re-render (316 regression)
- [440](./440.md) — Remaining section titles not headings (320 follow-up)
- [441](./441.md) — Home charts announced without curve name; iOS-only hint
- [442](./442.md) — Android reinstall never sets account-choice mark (318 sibling)
- [443](./443.md) — Delete/Edit on a plugin copy acts on the whole series
- [444](./444.md) — Padding entry detail turns "removed" after another entry opens
- [445](./445.md) — Money flow pads decimals only for USD
- [446](./446.md) — File editor load/reload failures have no Retry or message
- [447](./447.md) — Editor error banner matches a longer file name
- [448](./448.md) — Back during a last-file delete lands one folder too high
- [449](./449.md) — VoiceOver names a parent's (own) row as the parent
- [450](./450.md) — (own) row drops the parent's own EUR/commodity holdings
- [451](./451.md) — Fixed 0.005 tolerance folds BTC balances away
- [452](./452.md) — Picker hides Create for a full name that prefixes an account
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
- [315](./blocked/315.md) — In-app commits signed with Gitea username and real email (no full_name, no noreply) — **blocked:** needs the owner's noreply-address and published-history decisions, and a production backfill of existing Gitea users that can't be verified here
- [404](./404.md) — "Give it a review" opens a web listing that can't take a review
- [405](./405.md) — Settings drops Account section silently when profile fails to load
- [406](./406.md) — Reports/account detail use USD + English-root fallbacks before context loads (262/266 sibling)
- [407](./407.md) — APPLE *ICLOUD etc. lost Apple logo (270 regression)
- [408](./408.md) — Four-weekly series spanning Feb gets day anchor; Next ~5 days late (271 regression)
- [409](./409.md) — Cancelled semiannual bill stays Overdue ~17 months (267/269 follow-up)
- [410](./410.md) — Merchants splits NFC/NFD spellings of one payee
- [411](./411.md) — New Transaction: changing payee keeps first payee's accounts
- [412](./412.md) — Payee fill ranks FROM/TO independently; can fill same account twice
- [413](./413.md) — Parked keypad flow: overwrite, JPY ×100, double submit, closed accounts
- [414](./414.md) — Home 1M/3M count back from last entry, not today (240 sibling)
- [415](./415.md) — No operating_currency: Home shows $0.00 USD, all "Not in total"
- [416](./416.md) — Zero change from zero baseline reads "+$0.00" in gain colour
- [417](./417.md) — Latest Updates renders blank card on empty feed
- [418](./418.md) — Spending card never shows its two totals; empty ledger $0–$1 axis
- [419](./419.md) — Identical entries share entry_hash; Load more loops to page 1 forever
- [420](./420.md) — Account detail chart ignores price moves between postings, then jumps
- [421](./421.md) — FX conversion row shows only operating-currency leg
- [422](./422.md) — Units view sums cost of every commodity (+5 VOO at cost $0)
- [423](./423.md) — Closed accounts with balances vanish when siblings net to zero
