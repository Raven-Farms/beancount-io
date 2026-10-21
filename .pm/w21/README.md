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
