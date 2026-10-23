# Realized gains for a year

Read-only. Every figure comes from the `bea --json query` output quoted with
the answer — never from arithmetic done in prose. `$year_start` is the year's
first day, `$year_end` the next year's first day.

A closed lot is a reducing posting that carries a price: splits and
own-account transfers reduce lots without one, so the `price IS NOT NULL`
filter is what separates sales from movements. Proceeds use the posting's
price as recorded (`@@` totals are stored per-unit, so one formula covers
both forms); cost is the lot's own `cost_number`. Amounts are in each row's
cost currency — never sum across currencies.

<!-- recipe: realized-gains -->
```sh
bea --file "$ledger" --json --no-input query "SELECT account, currency AS commodity, cost_date AS acquired, date AS sold, (date - cost_date) AS held_days, -number AS quantity, -number * number(price) AS proceeds, -number * cost_number AS cost, (-number * number(price)) - (-number * cost_number) AS gain, cost_currency WHERE number < 0 AND price IS NOT NULL AND cost_number IS NOT NULL AND date >= $year_start AND date < $year_end ORDER BY date"
```

Present the rows as quoted, grouped into **held one year or less**
(`held_days` ≤ 365) and **held more than one year** (`held_days` > 365) —
the one-year boundary only, with no jurisdiction rules attached to it. Then
the engine-computed subtotals per holding bucket and cost currency:

<!-- recipe: realized-gains-totals -->
```sh
bea --file "$ledger" --json --no-input query "SELECT (date - cost_date) > 365 AS long_held, cost_currency, sum((-number * number(price)) - (-number * cost_number)) AS gain WHERE number < 0 AND price IS NOT NULL AND cost_number IS NOT NULL AND date >= $year_start AND date < $year_end GROUP BY long_held, cost_currency"
```

**Tie-out.** The per-lot gains must equal what was actually booked to the
ledger's gains account(s) that year. `$gains_pattern` matches the ledger's
own naming (for example `CapitalGains`); run it once per cost currency
present above:

<!-- recipe: realized-gains-booked -->
```sh
bea --file "$ledger" --json --no-input query "SELECT -sum(number) AS booked_gain WHERE account ~ '$gains_pattern' AND currency = '$currency' AND date >= $year_start AND date < $year_end"
```

Quote both outputs. If they disagree, say so and show both figures — a
difference means a gain was booked somewhere the lot rows do not explain
(a typed-in gain, a missing price, a differently named account). Never
adjust a row or a total to force the tie.

**Not covered:** open lots and unrealized gains (nothing here prices a
position still held — those are beancount-ask's holdings recipes in its
`references/bql-recipes.md`), positions without prices, wash sales, FX gains on
cash balances, and any tax form or jurisdiction rule. A reduction whose
posting carries no price is not a sale here; if the user says one was,
that is a fact to surface, not to price by guessing.
