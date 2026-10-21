# w21 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [x] **m1** — [Entry edits and deletes refuse changes that would break the ledger](./done/m1/README.md) (7 tasks) ← from mobile QA 2026-10-20

## Inbox

- [029](./029.md) — At AX2, New Transaction's posting accounts shrink to "Asse…cking" and "Ex…ries"
- [030](./030.md) — A transaction the ledger reports as broken opens with no sign of its error
- [031](./031.md) — New Transaction shows a green "✓ $0.00" remainder for an amount it refused to parse
- [032](./032.md) — A merchant whose name contains `"` opens with no header: the BQL escape `\"` is a syntax error on the rustledger engine
- [033](./033.md) — The Budget chart colors months before the budget existed red, as "over target"
- [034](./034.md) — Update Budget's amount field shows a stock "500" placeholder that reads as the current budget
- [035](./035.md) — Offset paging repeats a row when an entry is added between pages, and the lists append it without dedupe
- [036](./036.md) — The Transactions account filter offers only leaf accounts, so "all Food spending" can't be filtered
