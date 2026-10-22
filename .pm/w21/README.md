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
- [521](./521.md) — The file editor's error banner drops the fix hint Notifications shows (w21/424 incomplete)
- [522](./522.md) — After Overwrite or Recreate, the editor keeps the first-loaded text as its baseline, so a revert is never saved and Back loses it silently
- [523](./523.md) — Reports counts a bill pre-entered for later this month while Home's Spending stops at today (w21/337 sibling)
- [524](./524.md) — Home's Recent Transactions and Reports' account card key twin entries by the same `entry_hash` (missed by w21/419)
- [525](./525.md) — A guest journal link's filters follow the guest to every other example, and come back after Reset (w21/489 gap)
- [526](./526.md) — Transactions, Account and Merchant detail drop back to the newest 20 rows after a return to the app or any write; a stale "Couldn't load more" footer stays
- [527](./527.md) — A quick Back after deleting from a stacked detail still shows the deleted entry (w21/094 incomplete; w21/472 fixed only edit)
- [528](./528.md) — The Transactions filter's account picker offers "Create", which writes an `open` to the ledger
- [529](./529.md) — Month-end and quarter-end recurring bills show "Next" on the 30th instead of the 31st (w21/271 regression)
- [530](./530.md) — A new every-two-weeks payment spanning February reads "Twice a month", with Next up to 6 days late
- [531](./531.md) — The account picker offers "Create" for a closed account's short name, then Open Account refuses it
- [532](./532.md) — Account detail's "Off by" amounts land on the wrong balance assertion when the file isn't in date order (ledger)
- [533](./533.md) — A balance assertion failing its explicit `~` tolerance shows as passing: `diff_amount` is null for E2002 (ledger)
- [534](./534.md) — Booking and interpolation (`BOOK`) errors have no file or line, so the app can't open them (ledger)
- [535](./535.md) — Every dollar currency shows as "$" (¥ for CNY/JPY, kr for SEK/NOK), so a USD+CAD merchant shows two identical "$42.50" totals
- [536](./536.md) — In Persian, Money flow's cost/price line and the budget Delete alert put the currency on the wrong side (missed by w21/095 and w21/249)
- [537](./537.md) — The pending badge is a literal English "P" in all 13 languages
- [538](./538.md) — Scan Receipt's "Receipt read" shows a raw ISO date and an ungrouped total with no currency
- [539](./539.md) — Budget and Home show a refund month's Actual without its minus sign ("Actual $50.00 · Variance −$404.84")
- [540](./540.md) — Cash flow cuts off "(income)"/"(expenses)" on group names of 7+ characters, so both read "Interest …" (w0/034 incomplete)
- [541](./541.md) — Cash flow drops flows under 0.005 units whatever the currency, so BTC ledgers lose nodes and Savings is wrong
- [542](./542.md) — The balance chart's dashed start line and VoiceOver's "From" use the first point, while the change row uses the opening balance
- [543](./543.md) — VoiceOver says "+$0.00 since start" where the header shows a neutral "$0.00" (w21/416 half)
- [544](./544.md) — The editor's "View errors" pushes another Notifications; fixing from there leaves an outdated copy of the file open beneath
- [545](./545.md) — Incoming links to `/errors`, `/commits`, `/cash-flow`, `/trial-balance` and `/holdings` open Home instead of the matching screen
- [546](./546.md) — A next-day Create Ledger draft silently replaces a typed Books begin with today and reopens on Review (w21/053 over-applied)
- [547](./547.md) — Create Ledger accepts "___"-style names the server refuses, then shows only a generic retry error
- [548](./548.md) — Books begin in years 0001–0099 passes the form, but the server refuses it (`Date.UTC` in build-ledger) (backend-v2)
- [549](./549.md) — Create Ledger's "Amount owed" can't express a card in credit, and Review shows the opposite sign to the file
- [550](./550.md) — Stale-sha file delete: `BAD_USER_INPUT` on GraphQL vs `CONFLICT` on REST/MCP (Gitea's single-file 400 unmapped)
- [551](./551.md) — Deleting an already-gone file: `SERVICE_UNAVAILABLE` on REST vs `NOT_FOUND` on GraphQL/MCP
- [552](./552.md) — `previewLedgerSetup`/`createLedger` with `title: null` is a 500 on GraphQL; null amount/currency are wrongly refused
- [553](./553.md) — File create: REST commits "Update <path>" and refuses `""`, GraphQL commits "Create <path>" and accepts it
- [554](./554.md) — A holding that is also another lot's cost currency drops out of the holdings sheet, so BTC's stale price is never flagged
- [555](./555.md) — A commodity bought in two currencies shows bare "1.0 BTC" on its Accounts row, with no value or note
- [556](./556.md) — A holding priced only in an unrelated currency the account holds is labelled priced, though the ledger values it at cost
- [557](./557.md) — VoiceOver users can't remove a posting: "Remove posting" exists only as a swipe action
- [558](./558.md) — Menu items read their icon glyph as part of their name (MenuButton, missed by w21/141)
- [559](./559.md) — Account detail rows leave the type chip (Open, Close, Pad, Note) out of their VoiceOver label
- [560](./560.md) — Time-range pills are named only by abbreviations ("1M", "YTD", "1Г") for VoiceOver
- [561](./561.md) — The posting sign toggle reads only "Toggle amount sign": no plus or minus, and no posting named
- [562](./562.md) — The file editor's shortcut keys mostly read as just "Insert" (symbols unspoken, ⇥, raw ISO date)
- [563](./563.md) — Reports' Income/Expenses transaction cards look only at the 200 newest transactions, so a busy month hides the salary (w21/011 on Reports)
- [564](./564.md) — Creating an existing file now shows a generic failure on mobile: the server's new `CONFLICT` isn't passed through (w23/032)
- [565](./565.md) — New File's name check accepts names the server's new portable-path rule refuses (":", "?", "con") (w23/054)
- [566](./566.md) — Create Ledger says "already exists" for a renamed ledger's former name, which the server now reports as reserved (w23/061)
- [567](./567.md) — Server: pull requests refuse edits to existing legacy-named files, against w23/054's new-paths-only rule (backend-v2)
- [568](./568.md) — A transaction whose payee is only spaces shows as a blank row (and a blank detail title)
- [569](./569.md) — Searching Transactions or Merchants for "iş" misses payees with a Turkish "İ" (sibling of w21/060 and w21/257)
- [508](./blocked/508.md) — Mobile guesses that an entry is a plugin copy from its first line; read the ledger's `generated_from` instead (split from 443) — **blocked:** production's GraphQL schema lacks `generated_from` until the ledger service and backend-v2 deploy; mobile's client is generated from it
- [315](./blocked/315.md) — In-app commits signed with Gitea username and real email (no full_name, no noreply) — **blocked:** needs the owner's noreply-address and published-history decisions, and a production backfill of existing Gitea users that can't be verified here
