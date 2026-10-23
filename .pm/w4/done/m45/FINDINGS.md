# Commodity quantity presentation — actual statements and modeled Budget

**Severity:** minor financial presentation. **Owner:** dashboard. Continuous dashboard QA,2026-10-21. Promotes W4/331 without counting a duplicate group: both consumers route non-ISO quantities through the same cash-oriented formatter. The original complete Budget evidence is preserved below.

## Actual statement reproduction

Production `https://beancount.io`; isolated headless Chromium155.0.8059.85, anonymous English/light, fresh1440×1000 and390×844 contexts. These statement responses are actual public-ledger reads, not modeled values or clock overrides.

1. Open public `open_ledger/crypto-example` Trial Balance and select **Units** through the real native selector. The actual GetLedgerTrialBalance request returns HTTP200 with no GraphQL errors. Its Assets hierarchy has `Assets:Crypto:Wallet:MetaMask:ETH` balanceChildren **ETH:"4.00995"**. Options have render_commas=true and primary operating currency USD.
2. At both widths, the linked ETH row renders **ETH / - / 4.01 ETH** under Account/USD/Other. The390px listener ties that rendered row to the actual conversion:"units" response carrying4.00995. No document overflow, mutation attempt or page exception occurs.
3. In the narrow context, native Enter on that row opens its actual account journal with **Units** retained. Its newest2026-05-10 OpenSea row shows change0.60ETH and **Balance4.00995ETH**;11 rows including the header. The source digits remain available and the journal preserves them.
4. Use the actual Related pages navigation to Balance Sheet. Its Units selection persists; the same linked ETH row again displays **4.01 ETH** at390px. This confirms a second actual consumer of the shared renderer.

Passing Trial Balance controls at1440: API Coinbase BTC0.16 → **0.16 BTC**, and actual Checking USD68033 → **68,033.00**. This is precision-dependent commodity presentation; do not change the working cash policy. Income Statement/Cash Flow sharing is source-traced, not separately claimed as live fractional reproductions.

## Statement cause, source match and bounded acceptance

`dashboard/src/features/reports/balance-sheet/hierarchy-list.tsx` PrimaryCurrencyColumn (approximately75–81) coerces the raw amount to Number and calls useFormatNumber; OtherBalancesColumn (approximately100–133) drops source text while mapping to Number and calls the same formatter per commodity. The non-ISO grouped fallback caps at the locale default three fractional digits;4.00995 rounds to4.01. The ungrouped two-digit cap is source-traced only. Preserve the raw decimal's precision when formatting non-ISO quantities in both columns, while retaining ISO minor units and existing inversion/zero/disclosure behavior. Reuse existing quantity helpers; account readouts already demonstrate the intended source-aware contract.

Observed trial-balance asset imports led to the deployed `/lgassets/use-charts-visibility-Cw9D_NBi.js.map`. Its hierarchy-list.tsx SHA-256 exactly matches local main74684289b: **9f82e1b3e1dc1a176221387315f0268a7c00cabeb8e6b7714042ca6c7a11b54d**. Full deployed revision remains unverified. The shared cash formatter's exact deployed match is retained with the original Budget finding below.

Searched all board states for hierarchy, source precision, formatQuantity and commodity truncation. [W0/010](../../../w0/done/010.md) fixed consistent ISO cash precision and stated source-driven commodity behavior; this is the residual caller loss, not a reversal of cash precision. [W4/126](../126.md) fixed account tooltip precision with quantity helpers; the actual journal passes. [W3/192](../../../w3/done/192.md) reconciliation math and [W3/627](../../../w3/done/627.md) computed Overview table residue are distinct. Preserve [W4/081](../081.md), [201](../201.md) and [177](../177.md)'s extra-unit disclosure, click propagation and RTL repairs. No matching pending hierarchy precision repair found.

Ignored evidence: `dashboard/tmp/qa-20261020/dashboard-loop/crypto-hierarchy-quantity-complete-controls.json`, `crypto-hierarchy-eth-row-{1440,390}.png`, and a390px Balance Sheet page screenshot. The latter captures page layout; the ETH row is below its viewport, so the value claim uses the recorded actual row and response. Both contexts closed, hosted writes/fixtures0, modeled responses0, page/route errors0. No product fix or tests authored by QA. Implementation acceptance spans both renderers in the milestone rather than treating the old sub-hour Budget estimate as the combined scope.

---

# Preserved W4/331 evidence — Budget fractional readouts

**Original note estimate:** 45–60 minutes, superseded by this combined milestone. **Severity:** minor financial presentation. **Owner:** dashboard. **A2:** a reader budgeting in fractional commodities must see meaningful targets, actuals and differences rather than rounded zeros or a changed quantity.

## Reproduction and controls

Production `https://beancount.io`, 2026-10-21 America/Los_Angeles; owned isolated headless Chromium155.0.8059.85, signed out, English/light, fresh1440×1000 and390×844 contexts. **These are browser-local response fixtures against the deployed client.** The browser clock is explicitly September30,2026 at12:00UTC. Hosted budget contents and server budget calculations are unverified by these modeled values; no ledger is modified.

1. Independently read the public `open_ledger/budgeting-envelopes` response shapes: GetLedgerJournal has JournalResponse, seven Custom/budget entries with the expected fields; interval totals use IntervalTotalItem with date/balance/accountBalances. Real ledger options have render_commas=true and operating currency USD.
2. Before loading Budget, intercept only its Custom/budget GetLedgerJournal and the interval-total read for `Expenses:Qa-20261021:Precision`. Fulfill complete response fields using the actual shapes: one monthly directive effective2026-09-01 with amount **0.0004 BTC**, and one2026-09-30 period with actual/account balance **0.0005 BTC**. Each retained case fulfills these two reads once before transport; unrelated ordinary reads proceed normally.
3. After settlement, both widths show **Current budget 0 BTC**, **Latest actual 0.001 BTC**, **Above target**, and **Variance +0 BTC**. Expected quantities for this complete month are0.0004,0.0005 and+0.0001BTC.
4. Open **Period data** using native Enter. Its September30 row also says **0 BTC / 0.001 BTC**. Hover the actual canvas with the browser pointer: its real tooltip repeats **Budget: 0 BTC / Actual: 0.001 BTC** at both widths.
5. The target-history table correctly retains **2026-09-01 / Monthly / 0.0004 BTC**. The source amount remains available; display formatting loses it.

Fresh passing controls at the same month-end: a390px BTC model with0.004 target/0.005 actual displays0.004/0.005/+0.001BTC, and a1440px USD model with400.00/500.00 displays400.00/500.00/+100.00USD. Both keep Above target. The failing case's above-target status agrees with its inputs; retain that working comparison math. An initial real-clock October exploration was superseded because the existing sparse-current-month rule correctly inserted an October zero; no October actual-value defect is claimed.

## Cause and bounded repair

`dashboard/src/features/ledger-data/budget/budget-chart-card.tsx:85` uses useFormatNumber. Calls at262,390,400,441,519 and523 format the tooltip, three headline values and both Period data amounts through that cash-oriented formatter.

`common/hooks/use-format-number.ts:23–25` delegates to `common/lib/format/format-number.ts:14–44`. BTC is outside the ISO-currency set, so render_commas=true takes bare toLocaleString, whose default maximum is three fractional digits. Thus0.0004 becomes0 and0.0005 becomes0.001. The ungrouped branch caps at two digits; that branch is source-traced regression scope, not independently live exercised here. BudgetHistoryTable renders the original amount string and therefore preserves0.0004BTC.

Use the existing quantity-formatting support (`useFormatQuantity` / `formatQuantity` and source fraction information) for these non-ISO budget quantities, with sufficient precision to retain significant small targets, actuals and variance. Preserve locale/grouping behavior and meaningful recorded precision without displaying binary proration noise. Keep ISO currencies' intentional minor-unit presentation, period/target selection, numerical comparisons, empty/error handling and original history intact. The original Budget-only repair scope is extended by this milestone to the shared hierarchy; no global cash-formatter rewrite, decimal-arithmetic project, dependency or API change is indicated.

Acceptance: through the actual card and controlled real-query envelopes, assert the small BTC target/actual/+0.0001 difference in headlines, opened Period data and tooltip. Keep the larger-BTC/USD controls and source history correct, test grouping on/off and prorated/sparse-zero cases, and retain the relative-tolerance classification. Repeat desktop/narrow controls and run dashboard gates when implementing. Other commodities/locales, actual hosted fractional-budget creation and repaired behavior remain unverified.

## Dedupe, deployment and cleanup

Searched all board states for fractional budgets, BudgetChartCard formatNumber/quantity formatting and these small values, plus the relevant source history. [130](../130.md) fixes numerical proration residue and deliberately preserves commodity-relative tolerance; that comparison works here. [W21/290](../../../w21/done/290.md) owns the separate mobile implementation's fixed-cent arithmetic/classification; this note owns web display precision. [107](../107.md) adds the readable period alternative, whose displayed quantities now independently reproduce this formatter loss. No matching dashboard precision repair found.

Local main `74e70930c`. Public source maps exactly match local SHA-256: budget-CIotYHFT.js.map BudgetChartCard `f5fde58d974724393ba1fc440baf423b80ff3617a00a3cbe9dee16be89efd940`; use-format-number-DYYQJPsF.js.map hook `e09aba22eaed0fc7a7c814aedd7f6c65e4c6bab32d35f4b90ca686912f984ca7`; format-number-Dq7coopS.js.map helper `3ad91bfd4288575595b13934681a267ed6e9c3eb331368cd1a71889cd26fa918`. Full deployed revision remains unverified.

Ignored evidence: `dashboard/tmp/qa-20261020/dashboard-loop/budget-fractional-quantity-complete-controls.json`, `budget-fractional-modeled-{1440,390}.png`; narrow screenshot visually inspected. Four retained cases and one excluded exploratory context all close, leaving the original isolated QA context. Modeled reads forwarded, hosted writes, mutation attempts, fixtures, AI actions, route errors and page exceptions are0. No product fix or tests authored by QA.
