# w2 · m40 — Record everyday ledger changes through a `beancount-add` skill

**Worker:** worker2 **Goal:** a user who tells their coding agent "I paid $42 for dinner on the Amex", "open a savings account", or "close my old card" gets a proposed entry that uses existing accounts. It is written through `bea` only after a yes and checked against the root ledger, with the same safeguards the other skills use. **Status:** todo (t001–t002 done)

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| [t001](./done/t001.md) | Define the trigger, input contract, and name — **DONE** | 30m | w2/m38/t011 |
| [t002](./done/t002.md) | Write the `beancount-add` SKILL.md — **DONE** | 60m | t001 |
| t003 | Add executable recipes for close, price, and note | 45m | t001 |
| t004 | Write evals and fixtures | 45m | t002, t003 |
| t005 | Run the evals on Claude Code and Codex | 45m | t004 |
| t006 | Wire sibling hand-offs, inventory, and the suite count | 30m | t002 |
| t007 | Adoption surface | 30m | t005, t006 |
| t008 | Simplify | 15m | t007 |
| t009 | Test coverage | 30m | t007, t008 |
| t010 | Closeout | 15m | t009 |

## Definition of done

- `skills/.claude/skills/beancount-add/` exists, with a description whose triggers and skips route correctly in m38's routing set on both clients. The routing set gains its positive prompts, and the manual-entry prompts that were `none` now name it.
- The skill handles, for a local ledger: one or a few transactions described in words or pasted receipt text (including splits and transfers between the user's own accounts), opening an account, closing an account, a price, and a note. It routes bank exports, statements, migrations, and options trades to their siblings.
- Every write follows the suite's rules: a proposal showing the target file and exact entries, an explicit yes, existing accounts only (a new account only when the user asks for one), `Expenses:Uncategorized` when no confident account exists, a ±3-day same-amount check against entries that may already record it, writes through `bea add` with `--file` and `--into`, and a passing root `bea check` before success is reported.
- Closing an account with a nonzero balance is surfaced and never forced.
- New `<!-- recipe -->` blocks in the shared `bea-cli.md` are executed by `test_beancount_skills.py` against isolated ledgers.
- The skill's evals pass on Claude Code and Codex, recorded with versions and dates.
- The installer inventory, `skills/README.md`, `skills/AGENTS.md`, `skills/docs/installation.md`, and the root `README.md` describe a nine-skill suite.

## Source + Goal linkage

- **Source:** agentic-skill review of `skills/` at the user's request, 2026-10-18. The eight skills cover imports, statements, migration, questions, options trades, and closes. None owns the most common bookkeeping request, recording one thing the user just did. An agent therefore either picks a sibling built for something else or edits the ledger freehand, without the proposal, account, and check safeguards. `bea` already exposes the primitives (`bea add transaction|open|close|price|note|…`, `cli/src/cli/commands/add.py`).
- **Goal linkage:** **A1 — Agent-native accounting:** an agent can maintain a ledger day to day, not only in batch workflows. **A2 — Frictionless onboarding:** after `beancount-init`, the next thing a newcomer does is record a purchase.
- **Expected outcome:** a user records a purchase, transfer, new account, or account closure by describing it. The entry lands in the right file through `bea` and passes the check. Signals: routing-set recall for manual-entry prompts, and skill invocations once the registry listing exists.
- **Why now:** [ADR 020](../../../docs/adrs/ADR020-skills-accounting-workflow-candidates.md) requires a new top-level skill to have "a distinct trigger, input contract, deliverable, and evaluation set". [m38](../done/m38/README.md) supplies the routing evidence that shows the trigger is distinct. Shipping before [w6/m6](../../w6/blocked/m6/README.md)'s first ClawHub publish lets the listing go out as a complete suite. Sequence after [m39](../blocked/m39/README.md) when possible, so both milestones do not edit the same catalog lines at once. Adoption surface is included because this adds a customer-facing skill.

## Out of scope

- Editing or deleting existing entries. The suite appends only; a request to fix an entry is reported for the user to change.
- Balance assertions from a statement (`beancount-reconcile`) and options lifecycle events (`beancount-options`).
- A hosted-ledger variant (the MCP server's `addLedgerEntries` already covers hosted writes).
