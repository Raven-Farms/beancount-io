# Roll-forward calculation — tested against beanquery (beancount v3)

All queries below are verified. Run them with `bea --file "$ledger" --json --no-input query "$query"`; the shared command contract is in beancount-init's `references/bea-cli.md`. Adjust the placeholders (`<account>`, `<start>`, `<end>`) to the resolved account and half-open period (`<end>` is the first day after the period).

## The identity

For one account and one currency over `[<start>, <end>)`:

```
closing = opening + sum(signed movements)
```

- **Opening** is every posting to the account before `<start>` — including opening-balance entries. Nothing is special-cased.
- **Movements** are the signed postings inside the period, listed individually so each can be named by its counterparty, payee, or narration.
- **Closing** is every posting before `<end>`, computed independently — never as opening plus movements. The explanation is only valid when the two routes to closing agree exactly; any difference is reported, never plugged.
- **Cost basis by default.** Balances use `cost(position)`, so an inventory lot counts at what was paid. Market value is a separate, labelled column from `value(position)`, and only when the ledger's prices cover the period end; a missing price is a named gap, not a zero.
- **One currency at a time.** A query that mixes currencies returns mixed-unit rows; run the trio per currency and never add across currencies. Commodity units (shares) roll forward in units, separately from their cost.
- **Uncategorized is a visible bucket.** A movement whose counterparty cannot be named from the entry stays listed under `Uncategorized` with its date and amount. It is never dropped, netted away, or forced into a category to make the table tidy — an unexplained movement is the finding, not noise.
- **Negative and credit balances keep their signs.** A liability closing at −4,600.00 means 4,600.00 owed; state the direction in words instead of flipping signs silently.

## 1. Opening balance

<!-- recipe: rollforward-opening -->
```sql
SELECT sum(cost(position)) AS bal WHERE account = '<account>' AND date < <start>
```

## 2. Signed movements, one row each

<!-- recipe: rollforward-movements -->
```sql
SELECT date, payee, narration, cost(position) AS movement WHERE account = '<account>' AND date >= <start> AND date < <end> ORDER BY date
```

Name each row's bucket from the entry's other postings (the account(s) on the opposite side), falling back to payee, then narration; rows that resist all three are `Uncategorized`.

## 3. Closing balance (independent)

<!-- recipe: rollforward-closing -->
```sql
SELECT sum(cost(position)) AS bal WHERE account = '<account>' AND date < <end>
```

## 4. Market value at period end (only with covering prices)

<!-- recipe: rollforward-value -->
```sql
SELECT sum(value(position)) AS bal WHERE account = '<account>' AND date < <end>
```

## Worked tie-out (the eval fixture)

`Assets:PrepaidInsurance`, January 2026: opening 1,200.00; movements +600.00 premium top-up, −150.00 recognition; closing 1,650.00 — both routes agree. `Liabilities:Loan`: opening −5,000.00; movement +400.00 principal; closing −4,600.00 owed. `Assets:BrokerCash`: opening 2,000.00; movements −1,000.00 purchase, +25.00 dividend; closing 1,025.00.
