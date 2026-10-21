# w21 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [x] **m1** — [Entry edits and deletes refuse changes that would break the ledger](./done/m1/README.md) (7 tasks) ← from mobile QA 2026-10-20

## Dropped

- ~~**052**~~ — Drawer header words split mid-word at the largest text size — dropped 2026-10-21: reproduces only at AX5; at AX2 (`accessibility-large`) the header renders whole words (`.pm/DO_NOT_DO.md`, AX2 ceiling).

## Inbox

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
- [064](./064.md) — A token refresh whose response is lost signs the user out on the next refresh (rotated token replayed → grant revoked)
- [065](./065.md) — One early-year entry (e.g. 0050) makes the balance sheet 23,718 monthly points (3 MB) and the app stalls
