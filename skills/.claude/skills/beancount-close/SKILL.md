---
name: beancount-close
description: Close an accounting period in a Beancount ledger by reconciling each active account through beancount-reconcile, checking assertions and recurring gaps, reviewing flags, then proposing a commit with the period reports. Use for month-end close or wrapping up the books. Surface incomplete work and require a passing check before a confirmed commit; never push. Skip closing a single account (a `close` directive).
metadata: {"openclaw": {"homepage": "https://github.com/bex-co/beancount-io/tree/main/skills", "requires": {"anyBins": ["bea", "bean-check"]}, "install": [{"id": "brew", "kind": "brew", "formula": "bex-co/tap/bea", "bins": ["bea"], "label": "Install bea (Homebrew)"}, {"id": "uv", "kind": "uv", "package": "beancount-io", "bins": ["bea"], "label": "Install bea (uv)"}]}, "hermes": {"category": "finance", "tags": ["beancount", "accounting", "month-end-close", "reconciliation"]}}
---

# beancount-close

Close one month with a fixed, honest checklist — every account either ties out or is explicitly reported as unverified, and the close lands as a git commit whose message is the audit record.

This skill exists because trustworthy books come from ritual, not heroics: the same checks, every month, with nothing silently skipped. Each phase reports its status before the next begins; the final commit encodes the close report so `git log` reads as a close history.

## Prefer `bea`

Read beancount-init's `references/bea-cli.md` before running ledger commands: it defines explicit root/destination paths, JSON batches, checks, and safe retries. Without `bea`, use beancount-init's `references/compatibility.md`.

Check the root ledger and generate the committed summary with root-scoped
`report income-statement` and `report balance-sheet`, both using the resolved
month and both at book value (`-x at_cost`), the valuation the checklist's
period-end balances use. Reconciliation writes still belong to beancount-reconcile.

## Scope

**Does:** one period (default: last complete calendar month) across all active accounts; delegates per-account reconciliation to the **beancount-reconcile** skill; appends only what that skill's confirm-gated flow appends; produces a close report; makes one confirm-gated git commit.

**Does not:** fabricate missing entries (a missing subscription charge is *reported*, not invented); edit existing entries; force a tie-out; push to remotes (pushing stays with the user); close a period when the check is red — red blocks the commit proposal, always.

Read `references/close-checklist.md` before running — it defines each phase's procedure and reportable status.

## Workflow

Seven phases: **Scope → Reconcile → Assert → Recurring → Flags → Report → Commit.** Announce the phase status line as each completes (e.g. `Reconcile: 2 tied, 1 unverified (no statement)`).

### 1. Scope

Resolve the period (user's words or last complete month — state it). Find the ledger (same discovery as sibling skills). Enumerate **active accounts**: any Assets/Liabilities account with postings in the period or a nonzero balance at period end (bounded by `date < <period-end+1>`, so later entries don't count). Run `bea --file "$ledger" --json --no-input check` first — a ledger that starts red must be fixed (surface the errors) before a close can mean anything.

### 2. Reconcile

For each active account, ask the user for the period statement (CSV/pasted text). Per account **with** a statement, run the `beancount-reconcile` flow (its own confirm gate applies) — outcome **tied**, or **partial** when reconcile correctly withholds the assertion over unresolved suspects/mismatches (a reported finding with its residual, *not* a failure to retry). Per account **without** one: status **unverified** — listed in the report, never silently passed. Nothing in this phase writes except through reconcile's confirmed appends.

If beancount-reconcile is not installed beside this skill (a registry can install one skill alone), say so and point the user to https://github.com/bex-co/beancount-io/blob/main/skills/docs/installation.md to add it. Do not reconcile without it; continuing marks every account **unverified**.

### 3. Assert

After reconciliation, every reconciled account has a period-end `balance` assertion (reconcile appends them). Verify each active account has an assertion dated on/after period end; accounts without one are **unpinned** in the report.

### 4. Recurring completeness

Detect expected-but-missing entries: merchants (payee, or narration when the payee is empty) appearing in **each of the prior 2–3 months** (steady amount ⇒ subscription-like) but absent this period (query per `close-checklist.md`). Each gap is a **finding** ("NETFLIX appeared Apr+May, absent in June — charge missing, subscription cancelled, or card changed?") — the user answers; if a real entry is missing, it arrives via `beancount-import`/manual entry, **never fabricated** by this skill.

### 5. Flags

List every `!`-flagged entry dated in or before the period. Each is either resolved by the user now (their edit) or carried forward — counted in the report either way.

### 6. Report

Generate the period's numbers with the `close-income-statement` and
`close-balance-sheet` recipes in `references/close-checklist.md`: both reports
at book value (`-x at_cost`), so a cost-basis lot counts at its cost and a
commodity without a price (an `@`-priced foreign charge, an option lot) appears
in its own units instead of stopping the close. State that valuation in the
report. Expense totals in the operating currency come from beancount-ask's
`weight` recipes (`top-expenses` counts `300 EUR @ 1.10 USD` as the 330 USD
paid); without beancount-ask installed, report only the two reports. A report
that exits 1 with `result.missing_prices` is a valuation gap, not an engine
failure: list the missing prices in the close report and use the `weight`
recipes — never repair or reinstall the engine for it. Assemble the close report:

```
Close: 2026-06 (2026-06-01 … 2026-06-30)
Reconciled: Assets:Bank:Checking ✓ (ties to 7,874.60)     Unverified: Liabilities:CreditCard:Amex (no statement)
Assertions: 1 pinned, 1 unpinned
Recurring gaps: NETFLIX (present Apr, May — absent Jun)   Flags carried: 1 (2026-06-21 ! WHOLE FOODS)
Income: 3,000.00        Expenses: 203.60        Net: +2,796.40
check: PASS (`bea check`)
```

### 7. Commit

Re-run `bea --file "$ledger" --json --no-input check` after all reconciliation writes. Only when it passes, show what will be staged (the ledger files the close touched) and the commit message — subject `close: <period> — <n> reconciled, <m> unverified`, body = the close report. **Commit only on explicit yes.** On no: leave the working tree exactly as it is, report stays in the conversation. Never push.

## What NOT to do

- Don't skip or hide anything: unverified accounts, unpinned assertions, recurring gaps, and carried flags all appear in the report with counts.
- Don't fabricate entries to fill gaps or force assertions to pass.
- Don't propose the commit while the check is red.
- Don't commit or push without explicit confirmation (and never push at all).
- Don't re-implement reconciliation — delegate to beancount-reconcile per account.
