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
