# w3 · m57 — `beancount-accruals`: supported accrual drafts with explicit period policy

**Worker:** worker3 **Goal:** a new customer skill prepares deterministic, idempotent accrual drafts under an explicit period policy, posted only through the suite's existing propose/confirm/check flow. **Status:** todo (remaining t004, t005, t006, t007)

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](done/t001.md) | Define the schedule contract and deterministic calculation reference — **DONE** | 75m | — |
| [t002](done/t002.md) | Write the accruals skill with stable schedule identity — **DONE** | 90m | t001 |
| [t003](done/t003.md) | Write evals for partial periods, reversals, invoices, and reruns — **DONE** | 60m | t002 |
| t004 | Adoption surface | 30m | t003 |
| t005 | Simplify | 15m | t004 |
| t006 | Test coverage | 45m | t004 |
| t007 | Closeout | 10m | t005, t006 |

## Definition of done

- Each schedule states its policy and basis, service interval, day-count convention, recognized-to-date, already-booked, and required adjustment, with its support; cumulative-target and current-period-target schedules are distinguished.
- The ADR020 worked case is handled correctly in both states: $1,200 over twelve months with $200 still booked drafts $100; with $200 reversed it drafts the correct different amount, and a negative adjustment reverses direction.
- Rerunning a period reproduces the same draft and never a second posting; stable schedule/period identity and the canonical `import-id` convention guard externally sourced entries.
- No expense is inferred from a merely missing recurring payment, and no draft is posted or auto-reversed without the existing confirmed workflow.

## Source + Goal linkage

- **Source:** `/pm-brainstorm w3` 2026-10-20 candidate 5, from [ADR020 P1](../../../docs/adrs/ADR020-skills-accounting-workflow-candidates.md), including its correction of the upstream accrual shorthand.
- **Goal linkage:** A1 — Agent-native accounting.
- **Expected outcome:** freelancers and small businesses close months with accruals an agent calculated deterministically and a user approved, instead of estimates stated in chat. Signals: skill invocations, eval pass rate on both clients.
- **Why now:** sequenced after m55 and m56, whose movement and variance evidence its schedules cite; its policy contract (t001) is the risk to retire first. Adoption surface is included (t004) because a new customer skill ships.

## Prior blocker — cleared 2026-10-21

- **t003** — Claude Code evals pass 5/5; the Codex runs are quota-blocked at the account level. Unblock condition is written in t003.

The stale Codex quota condition is cleared by successful native runs recorded in `t003` and source `703fe36ca`; current client/source limits remain in the dated evidence. Continue the remaining tasks above.
