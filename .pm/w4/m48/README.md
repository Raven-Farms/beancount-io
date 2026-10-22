# w4 · m48 — Preserve receipt review through recording and failure

**Worker:** worker1 **Goal:** recording a reviewed receipt neither accepts disposable pending edits nor erases the review after a recoverable failure. **Status:** todo

**Severity:** minor. **Estimate:** 175m across six tasks, dashboard only. All upload/parse/write responses were intercepted or locally modeled; no hosted receipt booking occurred.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Lock payload-changing receipt review controls while recording | 40m | — |
| [t002](./t002.md) | Retain the reviewed draft and upload reference after recording fails | 50m | t001 |
| [t003](./t003.md) | Verify receipt review and recovery adoption guidance | 15m | t002 |
| [t004](./t004.md) | Simplify the receipt pending and failure state transitions | 15m | t003 |
| [t005](./t005.md) | Prove exact receipt review retention through completion and retry | 40m | t003 |
| [t006](./t006.md) | Verify repaired journeys and archive the milestone | 15m | t004, t005 |

## Definition of done

- [ ] Pending Date, Payee, Description, Amount, Currency and account/document controls cannot accept edits that the submitted snapshot's success will discard. Values/preview remain readable and one pending submit remains one request.
- [ ] A recording failure retains the exact reviewed values and uploaded receipt reference. A useful review/retry path requires no re-upload or re-parse and starts no automatic new write.
- [ ] A deliberate later submission uses the retained/current exact values once; submitted-snapshot success still shows those values. Do not infer that an ambiguous transport failure proves no booking occurred.
- [ ] Explicit Upload Different Receipt still resets intentionally. Upload/parse failures remain actionable; civil dates, exact signed postings, selected account/currency defaults, success navigation and duplicate-submit protection retain their behavior.
- [ ] Meaningful actual review/workflow regressions cover held success, failure, manual retry and reset. Fresh desktop/narrow guarded browser controls and dashboard gates pass.
- [ ] Adoption guidance stays accurate, simplification and test review complete, and /pm archives only after the observable end state holds.

## Source + Goal linkage

- **Source:** continuous $qa-find-bugs-dashboard,2026-10-22; [original973 pending-success evidence](./source-973.md) and [failed-record recovery evidence](./FINDINGS.md).
- **Goal linkage:** **A2 — Frictionless onboarding.** A newcomer can correct an extracted receipt and recover from a failed Record without reconstructing the review.
- **Expected outcome:** accepted receipt corrections survive recoverable recording failure, while pending controls honestly describe the snapshot already being submitted.
- **Why now:** both widths reproduce pending edits discarded at modeled success and exact pre-submit corrections discarded on injected recording failure. A control lock and a distinct workflow failure-state repair plus actual regressions exceed one hour; this promotion retains973 as one historical finding group. Adoption review applies to this customer-facing recording flow.

## Scope and dedupe

Own features/receipt only and existing supported common controls as needed. CSV Import [280](../done/280.md), New Entry [M33](../done/m33/README.md), shared pending focus [M42](../done/m42/README.md) and settings [M47](../m47/README.md) are separate callers. Backend receipt atomicity [W23/058](../../w23/done/058.md) remains unchanged. No API/dependency, persistent draft store, automatic resend or shared AI behavior change.
