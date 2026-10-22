# w4 · m50 — Retry failed statement, Account Journal and commodity reads

**Worker:** worker1 **Goal:** the failed report section can retry its own read without a document reload or preference reset. **Status:** todo

**Severity:** minor. **Estimate:** 160m across six tasks, dashboard only. This promotes328 with an independently reproduced Commodities caller; it is one historical callback-wiring finding group.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Wire the four statement and Account Journal retry callbacks | 50m | — |
| [t002](./t002.md) | Wire Commodities primary-read recovery through QueryView | 25m | t001 |
| [t003](./t003.md) | Verify recovery controls and adoption guidance | 15m | t002 |
| [t004](./t004.md) | Simplify the bounded observer retry wiring | 15m | t003 |
| [t005](./t005.md) | Prove scoped retry failure and recovery across the six observers | 40m | t003 |
| [t006](./t006.md) | Verify repaired journeys and archive the milestone | 15m | t004, t005 |

## Definition of done

- [ ] Trial Balance, Balance Sheet, Income Statement, Cash Flow's query-error branch, Account Journal and Commodities expose an in-place retry bound to their own failed observer.
- [ ] Retry keeps requested ledger/time/account/filter/conversion/chart selections and healthy sibling sections. Pending activation is safe; another rejection stays handled and retryable; success restores the current requested data.
- [ ] Commodities retry requests its price-history read without refreshing managed feeds or replaying any mutation. Preserve the separate acknowledgement/read contract owned by332.
- [ ] Cash Flow's accounting-reconciliation error retains its distinct semantics. Classified messages, loading/empty states, permission policy and successful data/exports remain correct.
- [ ] Meaningful actual query/component regressions and fresh desktop/narrow controls verify the boundaries, including rejected retry and eventual success. Dashboard gates pass.
- [ ] Adoption/simplification/test review completes and /pm archives only once the observable behavior holds.

## Source + Goal linkage

- **Source:** continuous $qa-find-bugs-dashboard,2026-10-21/22; [original328 report and Account Journal evidence](./source-328.md), plus [Commodities primary-read evidence](./FINDINGS.md).
- **Goal linkage:** **A2 — Frictionless onboarding.** A newcomer can recover the failed view where its error is shown while retaining the context they chose.
- **Expected outcome:** a transient read failure requires one discoverable retry, rather than learning reload or unrelated filter/navigation workarounds.
- **Why now:** All six observers now have independent desktop/narrow browser evidence; the newly deepened Balance Sheet, Income Statement and Cash Flow cases replace their earlier source-only limits. Six observer integrations and real regression coverage exceed the original sub-hour note. Adoption review applies to these customer-facing recovery controls.

## Scope and dedupe

Reuse existing ReportErrorState/QueryView onRetry support and each current observer. No global retry loop, document reload, dependency or API change. [337](../337.md) Holdings and [338](../338.md) Statistics use separate error renderers and remain separate work. [332](../332.md) owns managed-price mutation acknowledgement followed by read failure; this milestone's new Commodities case is its initial read with zero mutations. Other QueryView consumers and Account's separate primary-read branch are unverified audit scope, not added failures.
