# Commodities primary-read failure omits the existing local retry action

**Minor · dashboard.** Production https://beancount.io,2026-10-22; owned isolated headless Chromium155.0.8059.85, anonymous public open_ledger/example, English/light/UTC. Independent fresh390×844 and1440×1000 cases. Failures are explicitly injected before-transport aborts of GetLedgerCommodities, not observed service outages. All other reads remain real and available.

## Reproduction and controls

1. Open /ledger/open_ledger/example/commodities and abort only its initial GetLedgerCommodities. GetLedgerManagedPrices and the shared ledger reads are allowed.
2. Both widths show Error loading data / Failed to Load Commodities. The only button in main is Toggle Sidebar; there is no Try Again/Retry and no price-history disclosure.
3. Remove the fault. At1440, reload the same URL: six price-pair disclosures return, no error, and GLD/USD opens its142-row table including header.
4. At390, use the existing Related Pages Holdings link, wait for its real table, then browser Back. The original Commodities URL similarly returns six disclosures, no error and the exact GLD table: first2015-01-02 /167.19, last2017-09-08 /306.91.

The data is available and recovery workarounds work; the missing in-place observer retry is the defect. Independent ordinary history controls compare all141 GLD and141 ITOT values exactly with the actual API, with native Tab/End reaching the history bottom and disclosure collapse retaining focus. No chart-value or permanently trapped navigation bug is claimed.

## Source and bounded repair

features/ledger-data/commodities/index.tsx:157–168 obtains data/loading/error without refetch. Its QueryView at:179–199 supplies the error override but no onRetry. common/components/query-view.tsx already accepts onRetry and forwards it to ReportErrorState; that existing action renders only when a callback is supplied.

Wire the owning GetLedgerCommodities observer to the existing local action, handling pending/rejected retry and preserving its ledger/context, price history, loading/empty state and independent managed-source status. Retry this read, not RefreshLedgerManagedPrices or the whole document. The same callback omission is already owned by328 for five report/Account observers, so extend/promote that work instead of filing another historical group.

[332](../332.md) separately handles a successful managed-price mutation followed by a failed read; its truthful acknowledgement and recovery remain required. This primary-read case has no mutation, acknowledgement, refreshed source or quota action. The unrelated QueryView callers found in the source census are source-audit scope only; none is claimed independently broken here.

## Equivalent statements independently repeated

Additional fresh1440/390 controls now establish Balance Sheet, Income Statement and Cash Flow, beyond the original source audit. Let their actual server-prefetched first render settle before inducing a client read; an initial request guard alone cannot fail a cache-first observer whose data is already present.

- Balance Sheet and Income Statement: native Select conversion → Units, abort only the corresponding GetLedgerBalanceSheet/GetLedgerIncomeStatement. Both widths show the connection error, zero tables, no retry and no conversion control. Reload the same2016 URL and Units returns with no error; Balance Sheet tables have19/6/8 rows, Income Statement13/2/46.
- Cash Flow: keep At Cost and select Quarterly, then abort only GetLedgerCashFlow. The captured variables retain2016/at_cost/quarterly; both widths show the same error, zero tables and no retry. Reload returns the valid At Cost statement's four tables (52/7/13/7 rows). Reload resets the local interval to Monthly; this is explicitly a workaround, while the requested observer retry must retain Quarterly.
- Separate Cash Flow Units control correctly renders Cash flow cannot be reconciled, leaves conversion available, withholds export and recovers four tables after native At Cost selection. This is the intentional accounting-reconciliation branch, not another missing-retry defect.

`statement-equivalent-read-recovery-controls.json` records six retained statement cases, the adjacent reconciliation control and exact captured variables where available. Eight owned contexts closed across this deepening: six retained cases, the adjacent Cash Flow control and one earlier completed Income Statement case whose outer batch result was superseded. An initial prefetched-data wait and a table wait under the intentional Units reconciliation state were corrected and are not product failures. All requests are reads or pre-transport aborted reads; zero mutations, hosted writes, route errors or page exceptions.

## Source match and limits

Observed ledger._ledgerOwner._ledgerName.commodities-7qpCElkj.js.map matches current Commodities index SHA-256 **c4acb92af0cc3b1775d078b7b05bd85944b76811d654f4c673af4f85580d44ae**. query-view-DPGnQWqo.js.map matches current QueryView SHA **71f31523d3b579a9efe63fd8f2711168685bb3002930bc3c95819e2680bbe190**. Full deployed revision and repaired behavior remain unverified.

Ignored evidence under dashboard/tmp/qa-20261020/dashboard-loop: commodity-read-recovery-complete-controls.json, commodity-history-native-scroll-controls.json and commodities-read-failure-settled-390.png (visually inspected). The initial screenshots caught the entrance animation and are superseded for settled appearance; exact copy and absent action use recorded locators/buttons. One earlier case-sensitive copy wait was corrected and its owned context closed, not filed as a product bug. Two retained recovery contexts, one excluded wait context and one settled-screenshot context closed; zero mutations, hosted writes, route errors or page exceptions. Other engines, assistive-technology speech, the other primary-read consumers and actual outage behavior remain unverified. No product fix or authored tests.
