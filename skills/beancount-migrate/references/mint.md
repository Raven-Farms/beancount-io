# Mint export format

Mint's historical CSV (`transactions.csv`, the format users downloaded before the 2024 shutdown — frozen, will never drift):

```
"Date","Description","Original Description","Amount","Transaction Type","Category","Account Name","Labels","Notes"
"5/07/2026","Trader Joes","TRADER JOES #123 SEATTLE WA","54.20","debit","Groceries","Chase Checking","",""
```

Parsing rules:

- **Amounts are all positive**; `Transaction Type` gives direction: `debit` = money out of the account, `credit` = money in. Apply the account's ledger sign after mapping (asset out = `−`, etc.).
- **Dates are MDY** (`5/07/2026`).
- **`Description` vs `Original Description`** — Description is Mint's cleaned merchant (use as payee); Original Description is the raw bank string (use as narration when meaningfully different, and as the hash input for `import-id` — it's the stabler string).
- **`Account Name`** — the source account; one file covers all accounts, so this column drives the account mapping.
- **Transfer categories**: `Transfer`, `Credit Card Payment` (also `Transfer for Cash Spending`, `Cash & ATM` for some users — show the category list and let the user mark transfer-ish ones). Pair per mapping.md.
- **`Labels`/`Notes`** — carry into the narration or as `label:`/`note:` metadata if non-empty; drop if empty.
- Mint categories are a fixed taxonomy (~90 categories) plus user-defined ones; the mapping table will typically be 20–40 distinct values in practice.
- **No balances anywhere in the file** — opening-balance math per mapping.md is mandatory. The export ends at download (or the 2024 shutdown for old files) while any stated balance is newer, so the as-of gap rule always applies: never derive an opening from a post-export balance.
- **Split transactions** may appear as several rows sharing the date, account and `Original Description` with different categories and amounts. Ask whether each group is one split purchase and convert it per mapping.md's "Split purchases" (one transaction, one id over the total).
- Duplicates: Mint aggregation sometimes double-recorded a transaction (same date/amount/description, same account). Flag exact duplicate rows and ask, don't auto-drop — some are legitimate (two identical coffees).
