# w21 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [x] **m1** — [Entry edits and deletes refuse changes that would break the ledger](./done/m1/README.md) (7 tasks) ← from mobile QA 2026-10-20

## Dropped

- ~~**052**~~ — Drawer header words split mid-word at the largest text size — dropped 2026-10-21: reproduces only at AX5; at AX2 (`accessibility-large`) the header renders whole words (`.pm/DO_NOT_DO.md`, AX2 ceiling).

## Inbox

- [042](./042.md) — Mobile file editor silently corrupts non-UTF-8 files on save: "Café" becomes "Caf\uFFFD" (mobile counterpart of w4/276)
- [043](./043.md) — Mobile shows dates in years 0001–0099 as 1901–1999 (mobile counterpart of w4/277, w4/283 and w4/m38)
- [044](./044.md) — New Transaction's Done stays live while the save is in flight, so a second tap posts the entry twice
- [045](./045.md) — New Transaction's account picker offers closed accounts, and the save is then refused
- [046](./046.md) — Merchants merges payee case variants in the list, but the drill-down shows only one variant
- [047](./047.md) — Home's price-age warning reads a stale persisted price list after relaunch (`useLedgerPrices` still cache-first; residual of 006)
- [048](./048.md) — File editor's "File Changed → Reload" refreshes the text but keeps the old error list
- [049](./049.md) — Files locks every file named `main.bean`, not just the root one
- [050](./050.md) — Account detail shows Note, Balance and Document rows without their text, asserted amount or file
- [051](./051.md) — New ledger's "Books begin" defaults to the UTC date, so evening ledgers in the Americas start tomorrow
- [053](./053.md) — Create Ledger keeps its draft forever in AsyncStorage, opening balance included, and resumes stale dates
- [054](./054.md) — The drawer keeps listing a ledger that no longer exists across cold starts; choosing it shows only "Failed to load"
- [055](./055.md) — Reports keeps a "−$0.00 · 0%" row for a category that nets to zero; the Sankey can draw phantom nodes (float sums vs exact zero)
- [056](./056.md) — An account opened from the Accounts tab doesn't appear there after Done (`getLedger` not evicted by the write)
- [057](./057.md) — Mixed-currency entries get the wrong headline amount: a card purchase earning miles shows "+1,500.00 MILES"; an exchange flips sign by which leg has the `@`
- [058](./058.md) — In a non-USD ledger every USD balance is relabelled in the ledger's currency ("Bank €17,202.01"); Home shows a fake −98% crash
- [059](./059.md) — Transaction detail's Money flow drops lot cost and price (mobile counterpart of w4/220)
- [060](./060.md) — Account search misses accounts containing "İ" (Turkish dotted capital I)
- [061](./061.md) — Create Ledger suggests USD for Bulgaria (euro since 2026), Ukraine, Romania, Czechia…: hand-rolled list diverges from the setup catalog
- [062](./062.md) — The file editor converts CRLF files to LF on save: one added line rewrites every line ending
- [063](./063.md) — Budget "1Y" builds the invalid window `2023-02-29 - 2024-02-29` on leap days, so the view fails every 29 February
