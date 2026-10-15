# BQL recipes — tested against beanquery (beancount v3)

All queries below are verified against beanquery ≥ 0.2. Run them with `bea --file "$ledger" --json --no-input query "$query"`; the shared command contract is in beancount-init's `references/bea-cli.md`. The explicit developer fallback is in beancount-init's `references/compatibility.md`. Adjust date literals (`2026-06-01`) to the resolved period; date literals are unquoted. `~` is regex match.

## Sign traps (read first)

- **Income accumulates negative** (−3000 salary means $3000 earned). Negate for prose or use `neg()`.
- **Expenses accumulate positive** — totals read naturally.
- **Spend in the currency paid:** `weight` is what a posting cost in the currency it settled in — a `{cost}` lot at its cost, and an `@`/`@@`-priced foreign charge (`300 EUR @ 1.10 USD`) at the 330 USD paid. Use `sum(weight)` / `number(weight)` for USD spending answers. `cost(position)` converts only `{cost}` lots, so a priced foreign charge stays `300 EUR` and its number is compared as if it were dollars; keep it for book-value balances. `sum(position)` returns raw units (multi-currency ledgers render mixed units), and market value needs price directives and `value(position)`.
- **Spending ≠ cash out**: transfers and credit-card payments move money between own accounts. Selecting `account ~ '^Expenses:'` is what makes the recipes immune to that trap.

## 1. Top expenses (period)

<!-- recipe: top-expenses -->
```sql
SELECT account, sum(weight) as total
WHERE account ~ '^Expenses:' AND date >= 2026-06-01 AND date < 2026-07-01
GROUP BY account ORDER BY total DESC
```

Half-open period (`>= first, < first-of-next`) — never `<= last-day`, it drops nothing but reads wrong on time-of-day semantics elsewhere; consistency wins. Per-merchant variant: select `coalesce(payee, narration) as merchant` and `GROUP BY merchant` (imported one-description rows have an empty payee).

## 2. Monthly trend for one category

<!-- recipe: category-trend -->
```sql
SELECT year(date) as year, month(date) as month, sum(weight) as total
WHERE account = 'Expenses:Food:Groceries'
GROUP BY year, month ORDER BY year, month
```

Subtree instead of one account: `account ~ '^Expenses:Food:'`.

## 3. Net worth (book value)

<!-- recipe: net-worth -->
```sql
SELECT sum(cost(position)) as net_worth WHERE account ~ '^Assets:|^Liabilities:'
```

This is **cost basis**, not market value — say so when the ledger holds investments. Market value needs price directives and `value(position)`; if prices are missing, report that instead of a wrong number. Point at Fava's Balance Sheet for the browsable version.

## 4. Monthly burn (total spending per month)

<!-- recipe: monthly-burn -->
```sql
SELECT year(date) as year, month(date) as month, sum(weight) as spent
WHERE account ~ '^Expenses:'
GROUP BY year, month ORDER BY year, month
```

"Burn" for prosumers = expenses per month; net burn (spend − income) is this minus the same query over `^Income:` (negated). Flag outlier months rather than averaging over them silently.

## 5. Recurring charges & price creep

Candidates — same merchant hitting Expenses repeatedly. A merchant is the payee, or the narration when the payee is empty: `bea import` maps a one-description bank CSV to the narration, so grouping by `payee` alone lumps every imported row into one empty group.

<!-- recipe: recurring-candidates -->
```sql
SELECT coalesce(payee, narration) as merchant, count(date) as n, sum(weight) as total
WHERE account ~ '^Expenses:' GROUP BY merchant ORDER BY n DESC
```

A merchant with n ≈ months-in-ledger and steady amounts is a subscription; groceries/gas also recur — distinguish by *amount regularity*, and say which you excluded and why. Then per-merchant history to spot creep, using the `merchant` value from the candidates:

<!-- recipe: merchant-history -->
```sql
SELECT date, weight as amount
WHERE account ~ '^Expenses:' AND coalesce(payee, narration) = 'NETFLIX' ORDER BY date
```

Report creep as "was X through <date>, now Y (+Z%)".

## 6. Anomalies (unusually large transactions)

<!-- recipe: anomalies -->
```sql
SELECT date, payee, narration, weight as amount
WHERE account ~ '^Expenses:' AND number(weight) > 200 ORDER BY date
```

Set the threshold from context (e.g. ~3× the category's typical charge), and say what threshold you used. For "did anything unusual happen in <month>", combine with the period predicate from recipe 1.

## 7. Account balances / statement-style checks

```sql
SELECT account, sum(cost(position)) as balance
WHERE account ~ '^Assets:|^Liabilities:' GROUP BY account ORDER BY account
```

Point-in-time: add `AND date < 2026-07-01`. For "does this match my bank" → that's `beancount-reconcile`, not a query.

## Fava pointers

Top expenses / burn → Income Statement (filtered by time); net worth → Balance Sheet / Net Worth chart; per-payee history → Journal with `payee:"NETFLIX"` filter; account balances → Trial Balance. Give the user the Fava path when they want to browse rather than ask again.
