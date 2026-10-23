# First-year investor rehearsal record

Real-client rehearsals of the [first-year investor journey](first-year-investor.md),
kept separate from its deterministic verifier
(`scripts/skills/verify-first-year-investor.py`) and tests.

## Claude Code — 2026-10-20 ✅

A Claude Code 2.1.289 (`claude-opus-5-5[1m]`) session ran all eight stages
from the guide's prompts in a fresh scratch workspace (suite installed from
`eda6b446d`, `bea` 0.3.1), approving each proposal as a user would. Every
verifier checkpoint passed against the live ledger:
`initialized`, `seeded`, `purchased`, `imported`, `paid`, `swapped`,
`closed_june`, `year_end`. Per stage:

- Init proposed the 14 starter accounts plus the 8 investor/property opens
  with the booking-method explanation (FIFO written; STRICT left as the
  unwritten default) and wrote only after the yes.
- Seeding tied each export to its printed total before proposing
  (2600.00 broker, 20000.00 crypto) and kept printed acquisition dates.
- The purchase tied closing arithmetic (515000 both sides) and booked the
  510000.00 basis lot with a −400000.00 mortgage.
- The April import staged the buy (fee as its own leg), dividend, and FIFO
  sell with a booking-produced 1000.00 gain. One in-character observation:
  the agent flagged the brokerage's transient −1505.00 cash between the
  04-01 buy and the 04-03 sell and offered a deposit transfer; the import
  itself wrote exactly the three export rows and figures still tied.
- Four mortgage payments tied to each printed new balance; a fresh
  `Expenses:Interest` open rode along in the proposal.
- The swap disposed 0.2 BTC `@@ 12000.00` with a booking-produced 4000.00
  gain; June reconciled to 25400.00 (residual 0.00) and closed with the
  subject `close: 2026-06 — 1 tied, 5 not tied`, `main.bean` the only
  committed path.
- Year-end answer quoted the shown-query figures: lots worth 656000.00
  against 537600.00 cost, unrealized 118400.00, realized 2026 gains
  5000.00 tied to the booked total.

Two verifier defects were found by this rehearsal and fixed before the run
above (each with a regression test): checkpoints before any commit crashed
on the missing HEAD (`ce6de36a6`), and a close as the repository's first
commit diffed empty without `--root` (`eda6b446d`).

Not run: the guide's optional negative control (a mortgage total with no
printed split) — that behavior is covered by beancount-property eval 3.

## Codex — pending

Codex 0.163.0 returns its account usage-limit error until 2026-11-17, so
the journey has not run there. w2/m53/t003 reruns the identical prompts on
Codex when usage returns and records the outcome here.
