# Accrual schedule contract and calculation

All queries below are verified. Run them with `bea --file "$ledger" --json --no-input query "$query"`; the shared command contract is in beancount-init's `references/bea-cli.md`.

## The schedule

A schedule is a stated policy, never an inference. It names:

- **Identity**: a stable schedule id (`accrual:<slug>`) and the period it is being run for (`<schedule-id>:<period>`), so a rerun of the same period finds the same draft and never posts a second one. Entries an approved run writes carry that identity through the suite's canonical `import-id` convention (beancount-import's `references/dedup.md`), which is also how externally sourced entries in the same scope are recognised and kept out of the booked sum's blind spots.
- **Accounts**: the expense (or income) account and the balance-sheet account it accrues into (a liability for accrued expenses, an asset for prepaids).
- **Basis and support**: the total amount and what supports it (contract, invoice, approved estimate). An approved policy may rest on an estimate, but the method and source are written on the schedule; an unstated estimate is not a schedule.
- **Service interval**: the half-open `[start, end)` the basis amount covers.
- **Day-count convention**: `monthly` (equal months: basis × elapsed whole months ÷ total months) or `daily` (basis × elapsed days ÷ total days). The convention is part of the policy and is stated in every draft.
- **Target kind**: *cumulative* (the balance-sheet account should reach the recognized-to-date target; the draft is the difference) or *current-period* (this period's amount only, regardless of what is booked). The kind is stated; the two are never mixed in one schedule.

## The calculation

For a cumulative schedule at an as-of date inside the service interval:

```
elapsed        = whole months (monthly) or days (daily) of [start, as-of] ∩ service interval
target         = basis × elapsed ÷ total          (recognized to date)
booked         = expense already recognized in this schedule's scope: the net signed
                 postings to the balance-sheet account, read on the expense side
                 (negate a liability's signed sum; an asset's sum is used as-is)
draft          = target − booked
```

- **Booked is a net sum, not a list of prior accruals.** A reversal is a posting with the opposite sign, so it nets automatically. This is where the upstream shorthand — "periodic amount minus prior accruals minus invoices" — goes wrong: it subtracts gross prior accruals even when they were reversed, and double-counts invoices that were already paid through the accrual.
- **Invoices in scope are evidence, not a second subtraction.** An invoice that settles the accrued amount arrives as a posting against the same balance-sheet account, so it is already inside `booked`. It is listed in the draft's support, never subtracted again.
- **A negative draft reverses direction.** When `booked > target`, the draft is negative: the entry credits the expense (debits the balance-sheet account) instead of the usual direction. The draft states its direction in words.
- **Nothing is inferred from absence.** A missing recurring payment is not an expense; without a schedule (basis, interval, support) there is no draft.

## Booked to date (net, in scope)

<!-- recipe: accrual-booked -->
```sql
SELECT sum(cost(position)) AS booked WHERE account = '<accrual-account>' AND date < <as-of>
```

## Postings in scope (the draft's evidence list)

<!-- recipe: accrual-postings -->
```sql
SELECT date, payee, narration, cost(position) AS amount WHERE account = '<accrual-account>' AND date < <as-of> ORDER BY date
```

## The worked example (both states)

$1,200 over twelve months, `monthly`, cumulative, three months elapsed: target = 1,200 × 3 ÷ 12 = **300**.

- **$200 still booked** (one +200 accrual posting, nothing reversed): draft = 300 − 200 = **+100**.
- **$200 reversed** (+200 booked, then a −200 reversal): booked nets to 0, so draft = 300 − 0 = **+300** — a different amount. Any formula that subtracts "prior accruals" gross answers 100 here and is wrong.
- **Over-booked**: with +400 booked against the same 300 target, draft = **−100**, presented as a reversal of direction, not a smaller accrual.
