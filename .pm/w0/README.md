# w0 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [ ] **m1** — [Translate the English copies shipped in non-English catalogs, and guard against them](./blocked/m1/README.md) (8 tasks) ← from dashboard QA 2026-10-15 — **blocked:** live de/ru/zh check waits for a production deploy containing `036a499b`

## Dropped

- ~~**001**~~ — Close current-period earnings into equity on the hosted balance sheet — dropped 2026-10-15: superseded by [w6/m5](../w6/m5/README.md) (same root cause in the ledger balance-sheet producer). Additional evidence from this run: the Balance Sheet Markdown export labels a balanced ledger "internal draft" with a reconciliation difference equal to net profit, and the MCP `statements/balance-sheet` resource omits current earnings too.
- ~~**041**~~ — Browse ledgers' tab labels break mid-word at the largest text size — dropped 2026-10-15: reproduces only at AX5; at AX2 the tabs wrap on word boundaries ("Your / ledgers", "Starred", "Explore"). Out of scope per the `.pm/DO_NOT_DO.md` AX2 text-size ceiling.
- ~~**042**~~ — Settings' Invite Friends text breaks inside words at the largest text size — dropped 2026-10-15: reproduces only at AX5; at AX2 the summary breaks only between words. Out of scope per the AX2 ceiling.
- ~~**043**~~ — Account Picker's search placeholder is clipped at the largest text size — dropped 2026-10-15: reproduces only at AX5; at AX2 "Search accounts" renders whole and centered. Out of scope per the AX2 ceiling.
- ~~**044**~~ — Money flow shrinks accounts to ten characters at the largest text size — dropped 2026-10-15: reproduces only at AX5; at AX2 postings stay identifiable ("Assets:US…:Checking", "Income:US…le:Salary"), which is [w4/014](../w4/done/014.md)'s acceptance. Out of scope per the AX2 ceiling.

## Inbox

Mobile QA findings from 2026-10-15, triaged the same day. Order is suggested, highest impact first. Every note is sub-hour and owned by `mobile`, except 036, which also needs backend-v2.

**Majors: each can commit an invalid ledger in one tap**

- [037 — Open Account green-lights an account that is already open; Done writes a duplicate `open`](./037.md) — mobile QA 2026-10-15
- [038 — Add Budget accepts any amount text and writes it verbatim into an unparsable `custom "budget"` line](./038.md) — mobile QA 2026-10-15 (same file as 040; ship together)

**Minors: wrong or misleading output**

- [036 — Profile accepts usernames sign-up forbids; nothing server-side checks them](./036.md) — mobile QA 2026-10-15 (mobile + backend-v2)
- [045 — In Persian (RTL), text inputs stay pinned to the physical left (Profile, Payee)](./045.md) — mobile QA 2026-10-15
- [039 — Marking a merchant Recurring labels two identical monthly payments "Irregular"](./039.md) — mobile QA 2026-10-15

**Minors: polish**

- [040 — Add Budget's header Done skips the shared font-scale cap](./040.md) — mobile QA 2026-10-15, narrowed at triage to its AX2-reproducible part (same file as 038)
