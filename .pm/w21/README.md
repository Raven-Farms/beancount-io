# w21 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [x] **m1** — [Entry edits and deletes refuse changes that would break the ledger](./done/m1/README.md) (7 tasks) ← from mobile QA 2026-10-20

## Dropped

- ~~**052**~~ — Drawer header words split mid-word at the largest text size — dropped 2026-10-21: reproduces only at AX5; at AX2 (`accessibility-large`) the header renders whole words (`.pm/DO_NOT_DO.md`, AX2 ceiling).

## Inbox

- [064](./blocked/064.md) — A token refresh whose response is lost signs the user out on the next refresh (rotated token replayed → grant revoked) — **blocked:** needs an owner decision (ADR) on a refresh-token reuse grace window
- [065](./blocked/065.md) — One early-year entry (e.g. 0050) makes the balance sheet 23,718 monthly points (3 MB) and the app stalls — **blocked:** needs an approach decision (per-pill fetch vs server downsample) and a simulator profile of the stall
- [067](./067.md) — Transactions filter "Custom" seeds a 0–2 day window near month-end instead of last month
- [068](./068.md) — Notifications' Ledger Errors section shimmers forever when the errors query fails
- [069](./069.md) — Receipt capture prefills the amount at 2 decimals, so 3-decimal currencies lose precision
- [070](./070.md) — A JPY ledger shows "円1,500.00": wrong yen sign, prefix position, and forced decimals
- [071](./071.md) — Auth-error sign-out leaves the previous account's Create Ledger draft, Recent accounts and overrides
- [072](./072.md) — Account detail paging dedupes an overlap but never refetches, so a new entry stays missing
- [073](./073.md) — Renamed roots (`name_assets` …): Open Account can only write `Assets:…`; Reports' Recent transactions always empty
- [074](./074.md) — After the selected ledger is deleted, the drawer still pins it at the top as the current ledger (054 follow-up)
- [075](./075.md) — Multi-posting entry: a sub-cent leftover shows a red "+$0.00" that blocks Done; ".5" is refused
- [076](./076.md) — Home budget panel ignores the today cutoff and disagrees with the Budget screen; an overspent 0 budget reads "0% used"
- [077](./077.md) — Commit detail's VoiceOver stats label never pluralises ("+1 additions"; wrong ru/uk/sk/bg forms)
- [078](./078.md) — Transactions' 1M/3M/YTD filters freeze "today" when applied; after midnight new entries stay hidden
- [079](./079.md) — Entry writes leave the Files tab's file sha stale, so deleting that file fails until a refresh
- [080](./080.md) — A failed first load on Reports, Accounts and Home's budget panel reads as \$0.00 or "No accounts" (siblings of w4/067)
- [081](./081.md) — A failed pull to refresh wipes the loaded Transactions list and account journal
- [082](./082.md) — The Narration input never shows suggestions (the multiline layout dropped the list)
- [083](./083.md) — A ledger link opened while signed in stays stashed and replays on the next sign-in
- [084](./084.md) — Returning to the app resets a guest's example ledger: navigation and filters are thrown away
- [085](./085.md) — Open Account offers only operating currencies; its default sticks at "No currency" after a failed first load
- [086](./086.md) — Cancelling the RTL restart prompt leaves layout and language mismatched, and the prompt can't be brought back
- [087](./087.md) — A failing balance assertion looks like a passing one: the ledger service always sends `diff_amount: null`
- [088](./088.md) — Deleting a folder's last file will strand Files on "Failed to load" once w23/014's NOT_FOUND listing deploys
- [089](./089.md) — File editor error banner shows errors from same-named files in other folders
- [090](./090.md) — An app link to another ledger silently discards unsaved file-editor changes
- [091](./091.md) — File editor error rows say "line N" in English in every language
- [092](./092.md) — Entry Context balances: blank for zero, multi-currency run together as "100.00 USD,50.00 EUR"
- [093](./093.md) — A trailing-space payee splits a merchant: header "2 transactions · $3.00" over three listed rows totalling $7
- [094](./094.md) — A detail screen lower in the stack keeps showing a deleted or rewritten entry; its Edit then fails
- [095](./095.md) — Persian: signed amounts inside labelled lines render reversed (`1,234.50$- :مانده`)
- [096](./096.md) — Weekly/daily budget chart labels are US month/day in every language
- [097](./097.md) — Delete Budget alert is ungrammatical in de/nl/ru/uk/sk/bg (adverb used as adjective)
- [098](./098.md) — Reports/Budget chart VoiceOver summaries ignore plural forms ("over 1 months")
- [099](./099.md) — Accounts tab lists closed, emptied accounts as live "$0.00" rows
- [100](./100.md) — Multi-currency account journal shows "$0.00" rows and day totals for other-currency movements
- [101](./101.md) — Budget header says "Above target" in red for a period before the budget existed, over an all-grey chart
- [102](./102.md) — First bar of a 1Y / weekly-YTD budget chart is held to a whole period's budget for a partial period
- [103](./103.md) — New Transaction pre-fills a closed account as FROM when it was the most recently used asset
- [104](./104.md) — Create Ledger stores a liability opening balance with the wrong sign; the iOS keypad has no minus
- [105](./105.md) — Create Ledger's Review step: Create silently does nothing on a name conflict or bad amount
- [106](./106.md) — Create Ledger's opening balance dropped under "Decide later" or carried over from a previous preset
- [107](./107.md) — Create Ledger: free-text currency/date, raw server errors, and impossible dates (2026-04-31) accepted
- [108](./108.md) — "Choose from photos" fails for HEIC iPhone photos with "Could not read receipt"
- [109](./109.md) — Notifications bell never tells VoiceOver its error count
- [110](./110.md) — First New Transaction after relaunch pre-fills accounts from the stale persisted cache, even a deleted account
- [111](./111.md) — At AX2 the drawer clips "Ledgers", "+ New" and every ledger name to the top half of the text
- [112](./112.md) — Cash flow Sankey leaves refunds out of Savings, so Savings ≠ Net Profit and the VoiceOver summary contradicts itself
- [113](./113.md) — Journal account filter matches substrings: `Assets:Cash` also returns `Assets:CashApp` (REST/GraphQL/MCP)
- [114](./114.md) — Transactions search text carries over to another ledger after a drawer switch
- [115](./115.md) — Transaction filters survive sign-out and sign-in (missing from clearServerScopedState)
- [116](./116.md) — A load-more page landing after a filter/ledger change is appended to the new list
- [117](./117.md) — Saves/deletes show raw transport text ("Network request failed", "OAuth refresh failed"); no mobile raw-error guard
- [118](./118.md) — Merchants, merchant detail and Entry Context load errors append the raw Apollo message; two lack Retry
- [119](./119.md) — Session ending mid-action jumps to Welcome unexplained, under a raw "OAuth grant is no longer valid" alert
- [120](./120.md) — Saving an emptied Edit Transaction deletes the entry without confirmation and says "Transaction saved"
- [121](./121.md) — Update Budget keeps Currency editable; a non-operating currency silently becomes the first option
- [122](./122.md) — Account picker offers "Create" for a closed account; Open Account then says "already open"
- [123](./123.md) — Profile Save silently does nothing for a first/last name over 100 characters
- [124](./124.md) — Holdings bought in a non-operating currency get the wrong "priced / at cost (no price)" label
- [125](./125.md) — Holdings below 0.000001 units read "0 BTC" (exponential balance strings)
- [126](./126.md) — Fresh install ignores device language (English; Persian gets English in RTL that Settings can't undo)
- [127](./127.md) — Pending "P" badge is white on amber (~1.9:1 dark, 2.7:1 light)
- [128](./128.md) — Placeholders/labels use the hairline-border color as text (~1.34:1 light): Create Ledger, posting "Account", "Auto" tag
- [129](./129.md) — Browse ledgers → Starred stops after 30; local search can't find the rest
- [130](./130.md) — A starred private ledger never appears in Starred (admin client hides private stars; all surfaces)
- [131](./131.md) — App link with a differently-cased owner opens your own ledger read-only, without "Current"
- [132](./132.md) — Commit FILES list shows a rename as two "+0 −0" files; created and deleted files look identical
- [133](./133.md) — Commit per-file counts read 0 under `lib/`-style dirs and miss `---`/`++` content lines
- [134](./134.md) — Same-day entries are ordered by type, not file order, so account-journal running balances around a pad/note are wrong
- [135](./135.md) — Pad fires within balance tolerance: wrong balances and no "Unused Pad entry" error
- [136](./136.md) — Home's Latest Updates always requests the English feed
- [137](./137.md) — Ledger rows in Home's Latest Updates do nothing when tapped
- [138](./138.md) — Pull-to-refresh on Home doesn't refresh the bell's error badge
- [139](./139.md) — VoiceOver reads a Merchants row as only the payee (drops count, Recurring, cadence, Overdue)
- [140](./140.md) — VoiceOver on transaction rows omits narration and says "Pending" in English
- [141](./141.md) — Controls read with icon-font glyphs ("…U+F23B"), missing button roles; guardrail can't catch them
- [142](./142.md) — VoiceOver labels drop distinguishing text (file vs folder, template descriptions, which budget Update/Delete acts on)
- [143](./143.md) — No headings in journals, lists or cards; the Headings rotor can't navigate
- [144](./144.md) — File editor can't dismiss the keyboard for writable non-.bean files
- [145](./145.md) — Payee suggestions, Account Picker and Browse Ledgers can't bring last rows above the keyboard
- [146](./146.md) — New Transaction: with 4+ postings the number pad covers Add posting, Remainder and save errors
- [147](./147.md) — Latest Updates shows Blog/Release dates one day early west of UTC
- [148](./148.md) — Budget "Last year" uses the server's calendar, "This year" the device's — they disagree around New Year
- [149](./149.md) — New Transaction doesn't seed a payee's usual accounts when the name has punctuation (`Dupar's`, `Mr. Marcel`, `Chase:Slate`)
