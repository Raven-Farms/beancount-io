# Accrual schedule contract and calculation

All queries below are verified. Run them with `bea --file "$ledger" --json --no-input query "$query"`; the shared command contract is in beancount-init's `references/bea-cli.md`.

## The schedule

A schedule is a stated policy, never an inference. It names:

- **Identity**: a stable schedule id (`accrual:<slug>`) and the accounting period it is being run for (`<schedule-id>:<period>`), so a rerun of the same period finds the same draft and never posts a second one. Monthly periods use `YYYY-MM`, independently of daily or monthly day-count. The as-of date is an exclusive cutoff: as of 2025-02-01 closes January and uses `accrual:rent:2025-01`; March uses `accrual:rent:2025-03`, even when calculated on April 1. For a different reporting period, establish its stable identifier before drafting; do not substitute a run date. Entries an approved run writes carry that identity through the suite's canonical `import-id` convention (beancount-import's `references/dedup.md`).
- **Accounts**: the expense (or income) account and the balance-sheet account it accrues into (a liability for accrued expenses, an asset for prepaids).
- **Basis and support**: the total amount and what supports it (contract, invoice, approved estimate). An approved policy may rest on an estimate, but the method and source are written on the schedule; an unstated estimate is not a schedule.
- **Service interval**: the half-open `[start, end)` the basis amount covers.
- **Day-count convention**: `monthly` (equal months: basis × elapsed whole months ÷ total months) or `daily` (basis × elapsed days ÷ total days). The convention is part of the policy and is stated in every draft.
- **Target kind**: *cumulative* (recognized expense should reach the recognized-to-date target; the draft is the difference) or *current-period* (this period's amount only, net of recognition already booked in that period). The kind is stated; the two are never mixed in one schedule.

## The calculation

For a cumulative schedule at an as-of date inside the service interval:

```
elapsed        = whole months (monthly) or days (daily) of [start, as-of) ∩ service interval
target         = basis × elapsed ÷ total          (recognized to date)
booked         = net signed expense postings in this schedule's scope,
                 including recognition and its reversals, not funding or settlement
draft          = target − booked
```

- **Booked is net recognized expense, not the balance-sheet balance.** Expense reversals net automatically. Funding a prepaid asset or settling an accrued liability changes the balance-sheet account without recognizing expense; neither changes `booked`. For a prepaid premium of 1,200 with 100 recognized, the remaining asset is 1,100 but `booked` is 100.
- **Invoices in scope are evidence, not a second subtraction.** Include an invoice's expense recognition once when it is in the schedule's scope; a funding or settlement posting is support only. Never subtract the invoice amount again from the target or booked recognition.
- **A negative draft reverses direction.** When `booked > target`, the draft is negative: the entry credits the expense (debits the balance-sheet account) instead of the usual direction. The draft states its direction in words.
- **Nothing is inferred from absence.** A missing recurring payment is not an expense; without a schedule (basis, interval, support) there is no draft.

## Booked to date (net, in scope)

Use the stated expense account and exact balance-sheet account regex. These recipes assume that account pair identifies this schedule during the service interval. If several schedules share the pair, first resolve their entries from the supporting records and stable identities; do not count unrelated recognition. For a current-period target, bound recognition to that period instead of the full service interval.

<!-- recipe: accrual-booked -->
```sql
SELECT sum(cost(position)) AS booked WHERE account = '<expense-account>' AND has_account('<accrual-account-re>') AND date >= <scope-start> AND date < <as-of>
```

## Postings in scope (the draft's evidence list)

<!-- recipe: accrual-postings -->
```sql
SELECT date, payee, narration, cost(position) AS amount WHERE account = '<expense-account>' AND has_account('<accrual-account-re>') AND date >= <scope-start> AND date < <as-of> ORDER BY date
```

## The worked example (both states)

$1,200 over twelve months, `monthly`, cumulative, three months elapsed: target = 1,200 × 3 ÷ 12 = **300**.

- **$200 still booked** (one +200 accrual posting, nothing reversed): draft = 300 − 200 = **+100**.
- **$200 reversed** (+200 booked, then a −200 reversal): booked nets to 0, so draft = 300 − 0 = **+300** — a different amount. Any formula that subtracts "prior accruals" gross answers 100 here and is wrong.
- **Over-booked**: with +400 booked against the same 300 target, draft = **−100**, presented as a reversal of direction, not a smaller accrual.
