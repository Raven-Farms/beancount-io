# w0 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [x] **m1** — [Translate the English copies shipped in non-English catalogs, and guard against them](./done/m1/README.md) (8 tasks) ← from dashboard QA 2026-10-15
- [x] **m2** — [Structured ledger writes refuse changes that would break the ledger](./done/m2/README.md) (7 tasks) ← from /pm-brainstorm for w0 2026-10-17
- [x] **m3** — [Make i18n:prepare safe to run and honest about English copies](./done/m3/README.md) (8 tasks) ← from /pm-brainstorm for w0 2026-10-17

## Dropped

- ~~**001**~~ — Close current-period earnings into equity on the hosted balance sheet — dropped 2026-10-15: superseded by [w6/m5](../w6/done/m5/README.md) (same root cause in the ledger balance-sheet producer). Additional evidence from this run: the Balance Sheet Markdown export labels a balanced ledger "internal draft" with a reconciliation difference equal to net profit, and the MCP `statements/balance-sheet` resource omits current earnings too.
- ~~**041**~~ — Browse ledgers' tab labels break mid-word at the largest text size — dropped 2026-10-15: reproduces only at AX5; at AX2 the tabs wrap on word boundaries ("Your / ledgers", "Starred", "Explore"). Out of scope per the `.pm/DO_NOT_DO.md` AX2 text-size ceiling.
- ~~**042**~~ — Settings' Invite Friends text breaks inside words at the largest text size — dropped 2026-10-15: reproduces only at AX5; at AX2 the summary breaks only between words. Out of scope per the AX2 ceiling.
- ~~**043**~~ — Account Picker's search placeholder is clipped at the largest text size — dropped 2026-10-15: reproduces only at AX5; at AX2 "Search accounts" renders whole and centered. Out of scope per the AX2 ceiling.
- ~~**044**~~ — Money flow shrinks accounts to ten characters at the largest text size — dropped 2026-10-15: reproduces only at AX5; at AX2 postings stay identifiable ("Assets:US…:Checking", "Income:US…le:Salary"), which is [w4/014](../w4/done/014.md)'s acceptance. Out of scope per the AX2 ceiling.

## Inbox

From `/pm-brainstorm` for w0 (2026-10-17). Each note is sub-hour.

- [048 — Dashboard date-fns month names ignore the reader's language](./048.md) — dashboard
- [049 — Persian: letter-spaced captions break joins; Payee caption stays left; two inputs unverified in RTL](./049.md) — mobile
- [050 — German and Chinese use two words for "ledger" in the dashboard](./050.md) — dashboard
