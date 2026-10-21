# w4 · m38 — Accept supported early-year dates across directive writes

**Worker:** worker1 **Goal:** Valid canonical directive dates in years 0001–0099 survive shared validation, routing and serialization on every eligible API surface. **Status:** in progress (t001–t003 done)

**Severity:** minor. **Estimate:** 130m across six tasks, backend-v2 only.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Preserve the supplied year in directive calendar validation — **DONE** | 30m | — |
| [t002](./done/t002.md) | Preserve early-year routing and serialization in both write workflows — **DONE** | 25m | t001 |
| [t003](./done/t003.md) | Verify the date-input adoption surface — **DONE** | 10m | t002 |
| [t004](./t004.md) | Simplify the bounded calendar-date repair | 10m | t003 |
| [t005](./t005.md) | Prove strict-calendar behavior and eligible adapter parity | 45m | t003 |
| [t006](./t006.md) | Close out and archive the milestone | 10m | t004, t005 |

## Definition of done

- [ ] Valid 0001/0099 dates are accepted without remapping their years; the 0100 and modern-date controls remain correct.
- [ ] Structured entries and directive-text append preserve exact calendar dates in actual source and date-routed paths. Dry runs stay non-writing; successful application writes exactly once.
- [ ] Existing malformed/non-calendar-date refusals, year 0000 refusal, four-digit shape, useful field/index errors, authorization and atomic failure behavior remain intact.
- [ ] HTTP REST, real GraphQL execution and MCP-client regressions cover every eligible affected surface through both shared write workflows; accepted inputs, results, side effects and failure behavior agree under the existing credential policy.
- [ ] Backend typecheck/tests and OpenAPI drift validation pass with zero eligible parity gaps and unchanged frozen baseline/exception policy. No new dependency or cross-package import is needed.
- [ ] Record the tested target/build, exact cleanup and any production-deployment limit. No raw-file workaround substitutes for fixing the typed/text-write contract.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. See [the live API findings](./FINDINGS.md). **A1 — Agent-native accounting / A2 — Frictionless onboarding:** a human or agent must be able to submit a canonical date that the supported ledger engine and read APIs already accept. Live structured writes reject 0001/0099 while 0100 succeeds; text dry runs independently repeat the cutoff in REST and GraphQL. The shared guard is used before both structured-entry routing and text-append routing. Correcting the date constructor, checking routing/serialization and proving the eligible adapters exceed one hour. Adoption verification is included because this is a customer-facing write contract used by dashboard imports, CLI and agent clients. W4/277's separate CSV display issue remains independent; this milestone changes no dashboard code.

## Scope

Backend-v2's shared parseDirectiveDate and its two write consumers. Preserve strict invalid-date errors, operation/credential policy, quota behavior, allowInvalid semantics and source ordering. Do not introduce a new date format, broaden year 0000 policy, change the ledger engine, modify a caller's date or add a date bypass. The earlier report-document timeout remains unclassified. A later independent fixture completed actual dashboard exports and proved a separate dashboard period-construction defect, recorded in [W4/283](../done/283.md); it is outside this backend milestone.
