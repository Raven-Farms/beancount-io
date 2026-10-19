# Mapping strategy — categories, accounts, transfers, opening balances

## Account mapping (source accounts → Assets/Liabilities)

Type usually comes from the source (`Account Name` + account-type metadata, or the user). Checking/savings/cash → `Assets:Bank:<Name>` / `Assets:Cash`; credit cards → `Liabilities:CreditCard:<Issuer>`; loans → `Liabilities:Loan:<Name>`. Keep names short, CamelCase segments, and stable — they're forever. Sign rule after mapping: asset in = `+`; liability charge = `−`, payment = `+` (canonical detail — debit/credit split columns, sanity checks — in beancount-import's `references/formats.md` and beancount-reconcile's `references/statement-formats.md`).

**A liability's balance flips too.** Apps and banks show a card, loan or credit line's balance as the positive amount owed ("Amex 129.24"). On `Liabilities:…` that is `−129.24`; a card in credit (the issuer owes the user) is positive. Negate every stated current or opening balance of a liability before the opening math and the endpoint assertion.

## Category mapping (source categories → Expenses/Income)

Present the full distinct-category list with proposed targets as an editable table. Shaping rules:

- **Two levels max** to start (`Expenses:Food:Groceries`, not `Expenses:Food:Groceries:Organic`) — users can deepen later; collapsing later is painful.
- **Income categories** (Paycheck, Salary, Interest, Refund-like) → `Income:…`; remember beancount income is negative — the row's sign handles it, don't flip twice.
- **Merge near-duplicates** the app accumulated ("Coffee Shops", "Coffee") into one target — propose the merge visibly, let the user split if they object.
- **Refunds** in an expense category stay in that expense account (a positive Expenses posting is a refund, and that's fine).
- **No sensible target** → `Expenses:Uncategorized`, each such category listed with its row count in both the mapping table and the final report. Never guess.

## Transfer pairing

Transfer-ish categories (Mint: `Transfer`, `Credit Card Payment`; Monarch: `Transfer`; QBO: `Transfer` transaction type) describe **one** real movement that the export shows **twice** — once per account.

Pair rows where: both mapped as transfers, **same absolute amount**, **opposite directions**, **different source accounts**, dates within **±3 days** (symmetric — the same tolerance as beancount-import's fuzzy dedup layer). Each pair → one transaction:

```
2026-05-15 * "Payment to Amex"
  Assets:Bank:Checking          -450.00 USD
  Liabilities:CreditCard:Amex    450.00 USD
```

Greedy match closest-date-first; a transfer row with no partner (the counterparty account wasn't exported, or timing crossed the export boundary) is **unpaired**: convert it against `Equity:Transfers-Review` and list it in the report — totals still tie, the user resolves it later. Never drop it, never pair it with a non-transfer row.

Merged-pair transaction text: payee = the **outflow side's** description; keep the counterparty's raw description as narration when it differs meaningfully. Record one row's hash as `import-id` and the other's as `import-id-2` (see dedup.md) so either account's later import exact-matches its side.

## Opening balances and the endpoint assertion

Exports carry flows, not balances, so anchor both ends per account:

1. Ask the user for the **current balance** (from the old app's account screen or the real bank). Also ask for the **balance at the start of the export period** if they know it (or read it from the export when it states one). Put both in ledger sign: a credit card or loan is shown as the positive amount owed (`1,250.00`), which is `-1250.00` on a `Liabilities:` account; a credit balance becomes positive. When a liability balance arrives without a sign or an "owed"/"credit" word, **confirm it with the user before converting** — "Amex shows 129.24 owed → ledger −129.24, right?" — because step 2 cannot catch a flipped one:

<!-- recipe: liability-opening -->
```text
Amex balance 129.24 (owed)        current = -129.24
Σ converted Amex rows (ledger sign)         +370.76
opening = current − Σ rows        opening = -500.00
```
2. `opening = current − Σ(converted rows for that account)`. A derived opening makes the endpoint assertion pass whatever sign `current` had, so a positive card balance would migrate silently as money the bank owes the user (net worth too high by twice the balance) — the reason for step 1's confirmation. **But when a stated opening exists, use it as-is instead** — then the endpoint assertion is a genuine check of the conversion (rows missing from the export, pending transactions, wrong stated balance make it fail by exactly the delta), not a tautology. Never nudge either number to force a pass; a real delta is a report finding.
3. Initialize with opens dated on/before the **day before the earliest row**, then include the opening entry in the confirmed `bea` batch. Reuse the existing opening-equity account; `bea init` creates `Equity:OpeningBalances`:

```
2023-01-04 * "Opening balance (migrated)"
  Assets:Bank:Checking     212.55 USD
  Equity:OpeningBalances
```

4. Pin the endpoint with an assertion dated the **day after the last row** (beancount checks balances at the start of the date — same day-after rule as beancount-reconcile):

```
2026-07-16 balance Assets:Bank:Checking   3412.55 USD
```

A failing endpoint assertion is the migration's smoke detector — it means rows are missing from the export, pending transactions aren't in it, or the stated balance was wrong. Report the delta with those candidate causes. Only with the user's explicit acceptance, book the residual to `Equity:Migration-Residual` so the assertion passes *visibly* — never invisibly massage amounts.

## Split purchases

Some apps let the user split one purchase across categories, and an export may then show it as one row per category, each with the same date, source account and raw description:

```
"2026-03-12","Costco","Groceries","Chase Checking","COSTCO WHSE #0123","","-80.00",""
"2026-03-12","Costco","Household","Chase Checking","COSTCO WHSE #0123","","-40.00",""
```

The bank saw one charge, and its own export (what `beancount-import` reads after the migration) shows one row for `-120.00`. Converted row by row, the two pieces get two ids that match no bank row, so that later import books Costco again, or fails on the migration's own endpoint assertion by exactly the purchase amount. Ask the user about each such group (same date + source account + raw description, different categories; not a transfer pair). When they confirm a split, write **one** transaction: one source posting for the total, one counter-posting per category, and one `import-id` hashed over the **total** with the same normalization as any row:

<!-- recipe: split-purchase -->
```beancount
2026-03-12 * "Costco" "COSTCO WHSE #0123"
  import-id: "monarch:sha256:<16-hex of 2026-03-12|-120 USD|COSTCO WHSE #0123|Assets:Bank:ChaseChecking>"
  Assets:Bank:ChaseChecking  -120.00 USD
  Expenses:Food:Groceries      80.00 USD
  Expenses:Household           40.00 USD
```

When the user says the rows are separate purchases (two identical receipts on one day), keep them separate and say that a later bank import may list them as possible duplicates.

## import-id on migrated entries

Every converted entry carries `import-id` metadata using the `beancount-import` skill's convention (see that skill's `references/dedup.md`): native row ID if the export has one, else `<source>:sha256:<16-hex>` over the same normalized `date|amount|description|source-account` input (e.g. `mint:sha256:…`). A merged transfer pair records the second row's id as `import-id-2`. This makes migration and ongoing imports one continuous, deduplicated history: the user's first `beancount-import` run after migrating won't double-book overlap rows.

## Generic CSV path (unknown source)

Any export with date + amount + description + category + account columns migrates: confirm the column mapping and sign convention exactly as `beancount-import`'s formats reference prescribes, then follow this document from "Category mapping" on. Rows without a category all go to `Expenses:Uncategorized` — warn the user up front that refinement will be manual.
