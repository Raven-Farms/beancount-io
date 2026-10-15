# w0 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [ ] **m1** — [Translate the English copies shipped in non-English catalogs, and guard against them](./blocked/m1/README.md) (8 tasks) ← from dashboard QA 2026-10-15 — **blocked:** live de/ru/zh check waits for a production deploy containing `036a499b`

## Dropped

- ~~**001**~~ — Close current-period earnings into equity on the hosted balance sheet — dropped 2026-10-15: superseded by [w6/m5](../w6/m5/README.md) (same root cause in the ledger balance-sheet producer). Additional evidence from this run: the Balance Sheet Markdown export labels a balanced ledger "internal draft" with a reconciliation difference equal to net profit, and the MCP `statements/balance-sheet` resource omits current earnings too.

## Inbox

- [020](./020.md) — Name the header filter that failed to parse on reports and Journal (minor; dashboard; 45–60m).
- [021](./021.md) — Pluralize the profile follower count and call ledgers "ledgers" on profiles (minor; dashboard; 30–40m).
- [022](./022.md) — Accept Beancount's tolerance residuals in the Cash Flow conservation check, since At Cost is unusable on the public example (major; dashboard; 50–60m).
- [023](./023.md) — Explain that ledger names need Latin letters or digits when a non-Latin name is rejected (minor; dashboard; 20–30m).
- [024](./024.md) — Gate Upload Receipt on write access like Smart Import, and invite anonymous visitors to sign in (minor; dashboard; 40–55m).
- [025](./025.md) — Show the OpenSSH key format (ssh-ed25519 …) in the New SSH key dialog, not a PEM block (minor; dashboard; 20–30m).
- [026](./026.md) — Make a date-filtered Journal export load: carry opening balances or drop dependent assertions (minor; ledger; 45–60m).
- [027](./027.md) — Budget "This year" headline describes a future month, and "Last 12 months" prorates the current one (minor; dashboard; 40–55m).
- [028](./028.md) — Name each Budget history Delete button after the directive it removes (minor; dashboard; 15–25m).
- [029](./029.md) — Don't open Overview Money movement on an empty future month when a time filter is set (minor; dashboard; 25–35m).
- [030](./030.md) — Give the Overview Net Worth table view table semantics and a keyboard-scrollable region (minor; dashboard; 25–35m).
