---
name: beancount-close
description: Close an accounting period in a local Beancount ledger by reconciling each active account through beancount-reconcile, checking assertions and recurring gaps, reviewing flags, then proposing a commit with the period reports. Use for month-end close or wrapping up the books. Surface incomplete work and require a passing check before a confirmed commit; never push. Skip closing a single account (a `close` directive; beancount-add) and ledgers hosted on Beancount.io.
metadata: {"openclaw": {"homepage": "https://github.com/bex-co/beancount-io/tree/main/skills", "requires": {"anyBins": ["bea", "bean-check"]}, "install": [{"id": "brew", "kind": "brew", "formula": "bex-co/tap/bea", "bins": ["bea"], "label": "Install bea (Homebrew)"}, {"id": "uv", "kind": "uv", "package": "beancount-io", "bins": ["bea"], "label": "Install bea (uv)"}]}, "hermes": {"category": "finance", "tags": ["beancount", "accounting", "month-end-close", "reconciliation"]}}
---

# beancount-close

Close one month with a fixed, honest checklist — every account either ties out or is explicitly reported as unverified, and the close lands as a git commit whose message is the audit record.

This skill exists because trustworthy books come from ritual, not heroics: the same checks, every month, with nothing silently skipped. Each phase reports its status before the next begins; the final commit encodes the close report so `git log` reads as a close history.

## Prefer `bea`

Read beancount-init's `references/bea-cli.md` before running ledger commands: it defines explicit root/destination paths, JSON batches, checks, and safe retries. Without `bea`, use beancount-init's `references/compatibility.md`. This skill writes nothing itself: reconciliation writes go through beancount-reconcile, and its own output is the report and one commit.

## Scope

**Does:** one period (default: the last complete calendar month) across all active accounts; reconciles each account through **beancount-reconcile** and its confirm gate; produces a close report; makes one confirmed git commit.

**Does not:** create entries to fill a gap, edit existing entries, force a tie-out, or push. Every unverified account, unpinned assertion, recurring gap, and carried flag appears in the report with its count.

Read `references/close-checklist.md` before running — it defines each phase's procedure and reportable status.

## Workflow

Seven phases: **Scope → Reconcile → Assert → Recurring → Flags → Report → Commit.** Announce the phase status line as each completes (e.g. `Reconcile: 2 tied, 1 unverified (no statement)`).

### 1. Scope

Local ledger files only. If the ledger is hosted on Beancount.io and its MCP server is connected, use that server's `close-month` prompt and tools instead (beancount-init's `references/bea-cli.md`, Hosted ledgers).

Resolve the period (the user's words or the last complete month) and state it. Find the root ledger with the suite's discovery convention. Enumerate **active accounts**: any Assets/Liabilities account with postings in the period or a nonzero balance at period end (bounded by `date < <period-end+1>`, so later entries don't count). Run `bea --file "$ledger" --json --no-input check` first: a ledger that starts red is fixed (surface the errors) before a close can mean anything.

### 2. Reconcile

For each active account, ask for the period statement (CSV or pasted text). Per account **with** a statement, run the `beancount-reconcile` flow (its own confirm gate applies): the outcome is **tied**, or **partial** when reconcile withholds the assertion over unresolved suspects or mismatches (a reported finding with its residual, not a failure to retry). Per account **without** one, the status is **unverified** and the account is listed in the report.

If beancount-reconcile is not installed beside this skill (a registry can install one skill alone), say so and point the user to https://github.com/bex-co/beancount-io/blob/main/skills/docs/installation.md to add it. Without it, every account is **unverified**.

### 3. Assert

Every reconciled account now has a period-end `balance` assertion (reconcile appends them). Check that each active account has an assertion dated on or after period end; accounts without one are **unpinned** in the report.

### 4. Recurring completeness

Find expected-but-missing entries: merchants (payee, or narration when the payee is empty) present in **each of the prior 2–3 months** with a steady amount but absent this period (query per `close-checklist.md`). Each gap is a **finding** for the user ("NETFLIX appeared Apr+May, absent in June — charge missing, subscription cancelled, or card changed?"). A real missing entry is recorded through `beancount-import` or `beancount-add`, never created by this skill.

### 5. Flags

List every `!`-flagged entry dated in or before the period. Each is either resolved by the user now (their edit) or carried forward, and counted in the report either way.

### 6. Report

Generate the period's numbers with the `close-income-statement` and `close-balance-sheet` recipes in `references/close-checklist.md`, both at book value (`-x at_cost`) — the valuation the checklist's period-end balances use — so a cost-basis lot counts at cost and an unpriced commodity (an `@`-priced foreign charge, an option lot) appears in its own units. State that valuation in the report. Expense totals in the operating currency come from beancount-ask's `weight` recipes (`top-expenses` counts `300 EUR @ 1.10 USD` as the 330 USD paid); without beancount-ask installed, report the two statements only. A report that exits 1 with `result.missing_prices` is a valuation gap (beancount-init's `references/bea-cli.md`, Read and check): list the missing prices in the close report. Assemble the close report:

```
Close: 2026-06 (2026-06-01 … 2026-06-30)
Reconciled: Assets:Bank:Checking ✓ (ties to 7,874.60)     Unverified: Liabilities:CreditCard:Amex (no statement)
Assertions: 1 pinned, 1 unpinned
Recurring gaps: NETFLIX (present Apr, May — absent Jun)   Flags carried: 1 (2026-06-21 ! WHOLE FOODS)
Income: 3,000.00        Expenses: 203.60        Net: +2,796.40
check: PASS (`bea check`)
```

### 7. Commit

Re-run `bea --file "$ledger" --json --no-input check` after all reconciliation writes. A red check blocks the commit proposal. When it passes, show what will be staged (the ledger files the close touched) and the commit message — subject `close: <period> — <n> reconciled, <m> unverified`, body = the close report — and **commit only on an explicit yes**. On no, leave the working tree exactly as it is; the report stays in the conversation. Pushing stays with the user.
