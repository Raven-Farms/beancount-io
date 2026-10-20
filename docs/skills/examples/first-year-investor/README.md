# First-year investor sample data

All names, amounts, and IDs here are synthetic. Copy these files into a
separate run-owned workspace; never rehearse against personal books. They
ship inside the skills-only checkout alongside the installed customer
workflows.

One synthetic household year (2026, USD): an investor ledger initialized
2026-01-01 with 150,000.00 USD checking, existing VTI and BTC positions
seeded from cost-basis exports, a house purchase in February, broker
activity in April, four mortgage payments, a June crypto swap, a June
close against a one-row checking statement, and a year-end holdings and
realized-gains review.

| File | Purpose |
| --- | --- |
| `broker-holdings.csv` | Cost-basis export: two VTI lots + cash, total 2,600.00 |
| `crypto-holdings.csv` | Cost-basis export: one BTC lot, total 20,000.00 |
| `broker-activity.csv` | April activity: buy (fee itemized), dividend, sell |
| `loan-statements.md` | Printed principal/interest/escrow splits, Mar–Jun |
| `checking-statement-june.md` | June checking statement for the close (one row) |
| `expectations.json` | Independent checkpoint figures and the arithmetic behind them |

Do not insert the expected transactions directly as a shortcut: the
journey exercises the installed skills' review, confirmation, and
supported `bea` writes. A passing `bea check` is required at every
completed checkpoint, and every figure in `expectations.json` is
derivable from these inputs by the arithmetic recorded there — compare
observed figures (via `bea` queries) to those independent facts.

The accepted order matters where stated: seed before importing activity
(the April sell reduces a seeded lot under FIFO), record payments in
statement order (each ties to the printed new balance), and run the
year-end review only after the December prices are written.
