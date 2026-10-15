# w0 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Milestones

- [ ] **m1** — [Translate the English copies shipped in non-English catalogs, and guard against them](./blocked/m1/README.md) (8 tasks) ← from dashboard QA 2026-10-15 — **blocked:** live de/ru/zh check waits for a production deploy containing `036a499b`

## Dropped

- ~~**001**~~ — Close current-period earnings into equity on the hosted balance sheet — dropped 2026-10-15: superseded by [w6/m5](../w6/m5/README.md) (same root cause in the ledger balance-sheet producer). Additional evidence from this run: the Balance Sheet Markdown export labels a balanced ledger "internal draft" with a reconciliation difference equal to net profit, and the MCP `statements/balance-sheet` resource omits current earnings too.

## Inbox

- [007](./007.md) — Accept the bank amount spellings the CLI already imports in dashboard Smart Import CSV (minor; dashboard; 45–60m).
- [008](./008.md) — Return focus to the opener when the Journal New Entry dialog closes (minor; dashboard; 40–55m).
- [009](./009.md) — Bound the precision of Holdings' derived average cost (minor; dashboard; 25–40m).
- [010](./010.md) — Render report money at one precision per currency, independent of render_commas (minor; dashboard; ~60m).
- [011](./011.md) — Turn the Ask AI tool-activity counts into real plural messages (minor; dashboard; 35–50m).
- [012](./012.md) — Replace "(s)" count strings in Settings plan and Plaid flows with plural messages (minor; dashboard; 45–60m).
- [013](./013.md) — Give the ledger visibility switch an accessible name (major; dashboard; 20–30m).
- [014](./014.md) — Let keyboard users reach the clipped Other column in statement tables (minor; dashboard; 30–45m).
- [015](./015.md) — Meet the 24px target size for the ledger sidebar's inline actions and switcher (minor; dashboard; 40–55m).
- [016](./016.md) — Raise the contrast of the "Related Pages" heading (minor; dashboard; 10–15m).
- [017](./017.md) — Say why an Open Account name is invalid instead of one catch-all message (minor; dashboard; 30–40m).
- [018](./018.md) — Answer missing receipt assets and malformed OAuth links with 404/400, not a 500 "unexpected error" (minor; dashboard; 45–60m).
- [019](./019.md) — Tell `bea login` users their device code is unknown or expired, not "information provided is invalid" (minor; dashboard; 20–30m).
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
