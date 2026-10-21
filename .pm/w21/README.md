# w21 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [x] **m1** — [Entry edits and deletes refuse changes that would break the ledger](./done/m1/README.md) (7 tasks) ← from mobile QA 2026-10-20

## Inbox

- [038](./038.md) — Reports silently drops spending in other currencies; Home and Accounts say "not in total", Reports says nothing
- [039](./039.md) — Reports labels a net-negative category "0%" of its section
- [040](./040.md) — Mobile Budget applies the older of two same-date budget directives (mobile counterpart of w4/232)
- [041](./041.md) — Mobile Open Account rejects valid Hindi, decomposed-accent and titlecase names (mobile counterpart of w4/279)
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
- [052](./052.md) — At the largest text size the drawer's header breaks single words mid-word
- [053](./053.md) — Create Ledger keeps its draft forever in AsyncStorage, opening balance included, and resumes stale dates
