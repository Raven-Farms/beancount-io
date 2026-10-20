---
name: beancount-accruals
description: Prepare supported accrual and reversal drafts for a period from an explicitly stated schedule — basis, service interval, day-count, recognized-to-date, already-booked, required adjustment — posted only through the suite's propose/confirm/check flow with stable schedule identity. Skip recording one-off entries the user describes (beancount-add), explaining how a balance moved (beancount-roll-forward), tax or depreciation advice, automatic reversals, and ledgers hosted on Beancount.io.
license: MIT-0
metadata:
  openclaw:
    homepage: 'https://github.com/bex-co/beancount-io/tree/main/skills'
    requires:
      anyBins:
        - bea
        - bean-check
    install:
      - id: brew
        kind: brew
        formula: bex-co/tap/bea
        bins:
          - bea
        label: Install bea (Homebrew)
      - id: uv
        kind: uv
        package: beancount-io
        bins:
          - bea
        label: Install bea (uv)
  hermes:
    category: finance
    tags:
      - beancount
      - accounting
      - accruals
---

# beancount-accruals

Prepare an accrual draft a user can approve — **calculated from a stated schedule, never estimated in chat, and never posted without confirmation**.

This skill exists because period-end accruals are where agent arithmetic does the most damage: a plausible number, posted once, then posted again on rerun. So the calculation follows the contract in `references/schedule-contract.md` — **read it first** — every figure traces to a query or to the schedule's stated basis, and the draft carries a stable identity that makes a rerun reproduce the same draft instead of a second posting.

## Prefer `bea`

Read beancount-init's `references/bea-cli.md` (from this skill's folder, `../beancount-init/references/bea-cli.md`; a copy at `references/bea-cli.md` when this skill was installed alone) before running ledger commands: it binds the root ledger, the batch write path, and the check gate. Without `bea`, use beancount-init's `references/compatibility.md`. Writes go through `bea add` after confirmation, with decimal strings in batch JSON; `bea check` must pass before and after.

## Scope

**Does:** for each schedule the user states (or confirms from support they provide), compute recognized-to-date, already-booked, and the required adjustment per the contract, present the balanced draft entries, and — only on an explicit yes — post them through the shared propose/confirm/check flow.

**Does not:** invent a schedule from a missing recurring payment (absence is not an expense); post, auto-reverse, or schedule anything without the confirmation in this run; give tax or depreciation advice; modify existing entries — a wrong booked amount is surfaced, and its correction is the user's or beancount-add's.

## Workflow

### 1. Establish the schedule

Local ledger files only (hosted ledgers: beancount-init's `references/bea-cli.md`, Hosted ledgers). For each accrual the user wants, pin down the contract's fields: schedule id, expense and balance-sheet accounts (existing accounts only — categories are never invented), basis amount with its support, service interval, day-count convention, and target kind (cumulative or current-period). A policy may rest on an estimate the user approves, with method and source stated on the schedule. When any field is missing, ask; a draft built on an unstated assumption is an estimate wearing a schedule's clothes.

### 2. Compute and check identity

Run the contract's queries (`accrual-booked`, `accrual-postings`) for the as-of date. Before drafting, search the ledger for this run's identity (`accrual:<slug>:<period>`, carried as the entry's `import-id` on posting): if a posting with that identity already exists, the period is already drafted — show the existing entry and stop. A rerun must reproduce the identical draft, never a second posting. Externally sourced entries in scope are recognised by the same `import-id` convention and stay inside the booked evidence, never silently excluded.

### 3. Present the draft

Per schedule, show: the policy and its support, the interval and day-count, recognized-to-date, already-booked (with the postings list as evidence), and the required adjustment as balanced draft entries — direction in words when the adjustment is negative (a reversal of the usual direction). State the draft's identity. Nothing is written in this step.

### 4. Confirm, post, verify

Only on an explicit yes to the shown draft: write it through `bea add` with the identity as `import-id`, run `bea check`, and report the result. On no, nothing is written and the draft stays in the conversation. A reversal of a booked accrual is its own draft through the same flow — preparing a schedule never authorizes an automatic reversal later.
