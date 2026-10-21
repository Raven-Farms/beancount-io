# w21 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [x] **m1** — [Entry edits and deletes refuse changes that would break the ledger](./done/m1/README.md) (7 tasks) ← from mobile QA 2026-10-20

## Inbox

- [015](./015.md) — Home's lower cards keep their old text measurements when text size changes with the app open
- [016](./016.md) — Config plugins override the app's permission strings: a vague camera prompt, plus microphone and Face ID permissions the app never uses
- [017](./017.md) — With camera access denied, Scan Receipt hides "Choose from photos", so a receipt already in the library can't be scanned
- [018](./018.md) — Home's Spending chart gives VoiceOver axis ticks but never the two amounts it compares
- [019](./019.md) — In Persian, UI text left at natural alignment sits on the physical left, against `rtl.ts`'s documented rule
- [020](./020.md) — Once anything is Recurring, every merchant below appears to sit under the "RECURRING" heading
- [021](./021.md) — The account picker's Recent block ignores the selected root chip
- [022](./022.md) — A refund month's negative Expenses bar runs off the bottom of the Reports chart, through the month label
- [023](./023.md) — Picking a known payee in New Transaction doesn't bring its usual accounts, a capability lost when multi-posting became the default
- [024](./024.md) — Returning to the app never refreshes a mounted screen, so Home can contradict Transactions after an outside change
- [025](./025.md) — Searching `#tag` or `^link` in Transactions finds nothing, even for the tags the detail screen shows
- [026](./026.md) — Transaction Filters raises a duplicate-key error when a reversed custom range shows its message
- [027](./027.md) — At AX2, Budget card titles shrink to "Ex…ing" and "Ex…ries", so budgets can't be told apart
- [028](./028.md) — Saving over an entry changed elsewhere shows "Ledger resource not found" instead of w4/045's Reload choice
- [029](./029.md) — At AX2, New Transaction's posting accounts shrink to "Asse…cking" and "Ex…ries"
- [030](./030.md) — A transaction the ledger reports as broken opens with no sign of its error
- [031](./031.md) — New Transaction shows a green "✓ $0.00" remainder for an amount it refused to parse
- [032](./032.md) — A merchant whose name contains `"` opens with no header: the BQL escape `\"` is a syntax error on the rustledger engine
- [033](./033.md) — The Budget chart colors months before the budget existed red, as "over target"
- [034](./034.md) — Update Budget's amount field shows a stock "500" placeholder that reads as the current budget
- [035](./035.md) — Offset paging repeats a row when an entry is added between pages, and the lists append it without dedupe
- [036](./036.md) — The Transactions account filter offers only leaf accounts, so "all Food spending" can't be filtered
