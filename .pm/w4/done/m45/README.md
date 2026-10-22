# w4 · m45 — Keep commodity quantities precise in Budget and statements

**Worker:** worker1 **Goal:** readers can reconcile fractional commodity readouts with their ledger quantities. **Status:** todo

**Severity:** minor financial presentation. **Estimate:** 190m across six tasks, dashboard only. The observed defect changes displayed quantities; no underlying ledger or calculation corruption is established.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Preserve source precision in statement hierarchy cells | 40m | — |
| [t002](./t002.md) | Preserve meaningful fractional Budget readouts | 55m | t001 |
| [t003](./t003.md) | Verify quantity presentation and adoption guidance | 15m | t002 |
| [t004](./t004.md) | Simplify the bounded quantity formatting repair | 15m | t003 |
| [t005](./t005.md) | Prove real statement and Budget quantity rendering | 50m | t003 |
| [t006](./t006.md) | Verify repaired journeys and archive the milestone | 15m | t004, t005 |

## Definition of done

- [ ] Actual public crypto-example Trial Balance and Balance Sheet in Units retain the API's4.00995ETH in the account row, matching Account journal. Source precision survives primary/non-primary cells and inverted presentation where applicable.
- [ ] The modeled complete-month Budget target0.0004BTC, actual0.0005BTC and variance+0.0001BTC remain meaningful in headlines, opened Period data and tooltip. History remains correct; proration must not expose binary calculation residue.
- [ ] Preserve ISO currency minor-unit presentation, locale and render_commas behavior, zero suppression, signs, comparisons, account expansion and the accessible extra-unit disclosure. Larger-BTC and USD controls still pass.
- [ ] Reuse existing source-aware quantity formatting within the two consumers. No global cash-format policy change, dependency, API change, decimal-arithmetic rewrite or promise of arbitrary-precision numerical computation.
- [ ] Meaningful renderer regressions fail on the current truncation and cover grouping on/off, nonzero fine quantities, primary/non-primary commodities, inverted/multi-unit/zero cases, Budget proration and the cash controls. Dashboard format:check, lint, test and build pass.
- [ ] Repeat desktop/narrow journeys; distinguish actual public statement values from modeled Budget responses and record deployment status. Close/archive only once this observable contract holds.

## Source + Goal linkage

- **Source:** continuous dashboard QA,2026-10-21; promoted W4/331 with its complete modeled Budget evidence and added independently reproduced real statement precision loss. Reproduction, passing controls and source fingerprints are in [FINDINGS.md](./FINDINGS.md).
- **Goal linkage:** **A2 — Frictionless onboarding:** newcomers using fractional units can reconcile the first statement or budget with the source ledger without seeing significant quantities rounded away.
- **Expected outcome:** the same unconverted quantity remains recognizable across statement rows, account journal and Budget review, while cash amounts retain their intentional precision.
- **Why now:** source-aware quantity formatting already fixes account readouts, but the hierarchy and Budget still use a cash-oriented fallback. Two renderers, computed Budget precision and integrated regressions exceed a sub-hour note. Adoption review is included because these are user-facing financial readouts; no new package or workflow is introduced.

## Scope and dedupe

Dashboard shared statement hierarchy and Budget readouts only. [W0/010](../../w0/done/010.md) established consistent ISO cash precision; preserve it and complete its stated source-driven non-ISO behavior in these residual callers. [W4/126](../done/126.md) fixed account chart tooltip precision with existing quantity helpers; the actual journal control passes here. [W4/081](../done/081.md), [W4/201](../done/201.md) and [W4/177](../done/177.md) own already repaired disclosure, click propagation and RTL behavior. Keep those repairs. Do not alter report reconciliation math, conversion semantics or export scope. Full Budget-specific dedupe is retained in FINDINGS.
