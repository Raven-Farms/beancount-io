# w3 · m58 — Reconciliation exception register in `beancount-reconcile`, summarized by `beancount-close`

**Worker:** worker3 **Goal:** reconciling items that stay open across periods keep a stable identity, age, and disposition, and close reports them as open — never as resolved. **Status:** todo

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Define the register format and stable item identity | 75m | w2/m48/t008 |
| t002 | Carry open items forward in reconcile and summarize them in close | 60m | t001 |
| t003 | Adoption surface | 30m | t002 |
| t004 | Simplify | 15m | t003 |
| t005 | Test coverage | 45m | t003 |
| t006 | Closeout | 10m | t004, t005 |

## Definition of done

- Each open item records first-seen date (or unknown age when history is absent), amount and currency, source references, suspected cause labelled as suspected, owner only when supplied, and disposition.
- An item left open in one period appears in the next with correct age and the same identity even when the statement reorders its rows.
- Close's summary lists open, large, and old items and never counts an open item as resolved or upgrades a suspected cause to a confirmed one.
- Evals pass on Claude Code and Codex, recorded with versions and dates, alongside the existing reconcile and close evals.

## Source + Goal linkage

- **Source:** `/pm-brainstorm w3` 2026-10-20 candidate 6, from [ADR020 P1](../../../docs/adrs/ADR020-skills-accounting-workflow-candidates.md); w2/m48 names this register its natural follow-up and explicitly out of its own scope.
- **Goal linkage:** A1 — Agent-native accounting.
- **Expected outcome:** users reconciling monthly stop re-discovering the same open items every period; agents carry them forward with their history intact. Signals: repeat reconcile invocations per account, eval pass rate on both clients.
- **Why now:** it builds on w2/m48's coverage preflight (t001–t003 done); t001 is gated on m48's closeout so the two reconcile changes do not collide. Adoption surface is included (t003) because two customer skills change behavior.
