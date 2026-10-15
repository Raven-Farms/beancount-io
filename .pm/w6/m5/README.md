# w6 · m5 — Include current earnings in balance-sheet equity

**Worker:** worker1 **Goal:** An unfiltered balance sheet includes the selected period's earnings in its equity hierarchy and series, so the same books reconcile in their active year and the following year. **Status:** todo (t001, t002 done)

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Close current earnings into the balance-sheet equity hierarchy — **DONE** | 45m | — |
| t002 | Apply the same earnings policy to equity chart points — **DONE** | 25m | t001 |
| t003 | Adoption surface | 15m | t002 |
| t004 | Simplify | 10m | t003 |
| t005 | Test coverage | 35m | t003 |
| t006 | Closeout | 10m | t004, t005 |

## Definition of done

For the fictional public-company-template ledger with time=2025, MCP/REST balance-sheet summaries and the underlying GraphQL hierarchy report 23,000 MUSD assets, -10,000 liabilities and -13,000 equity, including -3,000 current earnings. Signed assets+liabilities+equity is zero at cost. The 2026 control keeps -3,000 previous earnings without double counting current earnings. Equivalent native synthetic fixtures, custom earnings/root names, loss/zero-profit cases and equity series points follow one closing policy. Income-statement, trial-balance and journal data retain their own semantics; no report read writes closing transactions to source. Eligible REST/GraphQL/MCP contracts and owning package checks pass. Account-filtered reports retain their documented scope rather than claiming unconditional full-ledger reconciliation.

## Source + Goal linkage

- **Source:** Live functional MCP QA on 2026-10-15; major financial-report defect in the ledger producer, with backend-v2 validation.
- **Goal linkage:** A1 — agents can trust a balance-sheet equity total without manually adding a separate income statement.
- **Expected outcome:** The active-year and next-year statements account for the same 3,000 MUSD profit exactly once, and equity charts agree with their closing hierarchy.
- **Why now:** A previously unexercised fictional MUSD fixture exposes a shared missing report-closing step. This is executable local report work, not blocked on a WASM release. It spans hierarchy policy, chart policy and regression/parity checks, so it is a roughly 2h milestone rather than a sub-hour inbox note. Adoption surface is included because this changes agent-visible financial output.

## Live reproduction and controls

Target `https://beancount.io/api-gateway/mcp`; last observed server beancount-mcp 1.0.0, protocol 2025-11-25; deployed backend/engine revision unavailable. Designated unpinned API key has ledger.read/write/admin scopes; no writes were made. The public fixture source explicitly states that Example Industries Inc. and all figures are fictional teaching data. It has 17 Pads/Balance assertions, 26 Opens, one authored income transaction and 17 generated padding transactions. Official Beancount validates the in-memory fixture and its padding matches the served journal.

```sh
node .agents/skills/qa-shared/scripts/qa-mcp.mjs --credentials-file .env read 'beancount://open_ledger/public-company-template/statements/balance-sheet?time=2025'
```

Two fresh MCP/REST requests return currency MUSD, assets 23000, liabilities -10000, equity -10000, netWorth 13000, with no current-earnings account. The 3000 gap exactly matches the 2025 income statement: income -20000, expenses 17000, net 3000. GraphQL getLedgerBalanceSheet(time:"2025") returns identical root balanceChildren totals 23000/-10000/-10000. All are successful responses, not malformed-input or entitlement failures.

Control time=2026: same assets/liabilities, equity -13000 including Equity:Earnings:Previous -3000, netWorth 13000. A second synthetic ledger, freelancer-invoicing time=2026, has assets/netWorth 30950 and equity -16500 on MCP/REST; current profit accounts for the missing 14450, independently computable from its complete journal. The second ledger's current-earnings behavior is reproduced, but no UI journey is claimed.

Official installed Beancount over the fictional company source, entirely in memory: clamp_opt for [2025-01-01,2026-01-01), then clear_opt at the end, yields Equity:Earnings:Current -3000 and total equity -13000. The source remains unchanged. [Fava's FilteredLedger.root_tree_closed](https://github.com/beancount/fava/blob/main/src/fava/core/__init__.py) caps its report tree; [Tree.cap](https://github.com/beancount/fava/blob/main/src/fava/core/tree.py) includes income/expense balances in the configured current-earnings account. These sources were inspected; a running upstream Fava deployment was not tested. Do not copy upstream implementation code into this repository.

## Root cause and bounded scope

`backend-cluster/ledger/src/features/ledger/service/ledger-finance-service.ts::getBalanceSheet` uses the ordinary clamped report stream for accountHierarchy and accountBalanceSeries over only the equity root. `loadReportDirectives` summarizes pre-period income into previous earnings, but no balance-sheet-only current-period closing step is applied. `ClampAccountOptions`/ReportAccounts only carry the earlier-earnings and conversions targets, so the current-earnings option is not threaded into this producer. The hierarchy omission is live-proven; the equity-series omission is source-traced and must be verified in t002.

Fix the native producer and shared naming/closing policy, then verify backend-v2's summary, Fava-shaped resource and GraphQL mappings. Adding 3000 only to the MCP/REST summary would leave the root hierarchy and charts wrong. Reuse the existing cost-aware inventory and option machinery, honor configured names, and keep synthetic report effects out of editable journals and persisted files. No dependency, parser, currency-conversion redesign, artificial source closing entry or new endpoint is needed. Unrealized market gains and conversions are not independently reproduced by this single-currency example; preserve their existing behavior and do not claim this fixture verifies them.

## Dedupe and retained evidence

Searched all board states for missing current earnings, balance-sheet equity closing and reconciliation. w6/006 owns zero-net currency selection and w6/009 valuation-snapshot selection, both source-fixed; neither synthesizes current earnings. w6/022 owns BQL OPEN/CLOSE windows, not this report producer. w3/395 and CLI w5/127 concern account filters and valuation adjustments in the Python reporting path. w4/080 checked MUSD labels and the 2026 control, not active-year closing. Current producer history has no later closing implementation.

Ignored evidence in `.tmp/qa-2026-10-11/mcp-loop/`: company-statement income/balance, repeated company-equity-2025, next-year company-equity-2026 MCP/REST; GraphQL company-current-earnings; official company-current-earnings-python-control; fictional company source/header and pad controls; invoice-current-equity-control; inspected Fava core/tree source snapshots. No credentials, private data, engine bytes or product changes are committed.
