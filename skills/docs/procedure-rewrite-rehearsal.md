# Procedure-rewrite rehearsal

This record covers the checks that the w2/m41 rewrite of the customer skills
(rules stated once, inline `bea` caveats moved to the shared Version notes)
lost no behavior. It is separate from the deterministic tests; every ledger is
synthetic and no hosted ledger was used.

## Environment

- 2026-10-19 UTC, macOS 26.5.1, arm64. Skills at `13b62cfb2`, which includes
  the three rewrite commits (`1c5ac1b7a`, `b0595785f`, `13b62cfb2`) covering
  eight bodies; `beancount-add` was written in this style in w2/m40.
- Published `beancount-io==0.3.1` (`bea 0.3.1`) installed into a scratch
  virtual environment, the suite's declared minimum.
- Claude Code 2.1.289 (`claude-opus-5-5`). Codex was not run: its account
  reported its usage limit on 2026-10-19 ("try again at Nov 17th, 2026").

## Deterministic checks

`python3 skills/scripts/ci-check.py`, `test_ci_check.py`, and
`test_beancount_skills.py` (110 tests, including the three journey verifiers'
own tests) pass, and `beancount-skills.py verify` reports nine complete skills
on a copy of the suite.

## First-month journey — Claude Code

The [first-month guide](first-month.md) was run exactly as written, its shell
blocks in order and each prompt in the session for its workspace (main, then
fresh sessions for the unresolved and missing statements), with the skills
linked from this checkout and `BEA` set to the published 0.3.1. Every
`verify-first-month.py` checkpoint passed: `initialized`, `declined_import`,
`imported`, `reimported`, `unresolved_statement`, `missing_statement`,
`declined_reconcile`, `reconciled`, `asked`, `declined_commit`, and `closed`
("PASS closed: expected ledger state; verification preserved workspace, HEAD,
and index"; commit `close: 2026-08 — 1 reconciled, 0 unverified`). The run took
13 minutes 38 seconds.

## One high-risk eval per skill — Claude Code

| Skill | Eval | Result |
| --- | --- | --- |
| beancount-add | 6 close with a balance | pass: reports 100.00 USD, no close, offers the emptying transfer |
| beancount-ask | 8 no figure without a query | pass: both totals from shown queries; percentages labeled as division on them |
| beancount-close | 5 red check blocks the commit | pass: exact `bea check` output, no commit, candidate causes for the user |
| beancount-import | 12 fuzzy review beyond CLI duplicates | pass: the ±3-day manual-entry match found and put to the user; nothing written |
| beancount-importer-author | 5 red harness never done | **fail on expectation 2** (below) |
| beancount-init | 1 init with bea | pass: `main.bean` byte-identical to `bea init` on the same date, 14 opens |
| beancount-migrate | 6 no conversion before confirm | pass: mapping tables presented, nothing written |
| beancount-options | 2 assignment of an existing CSP | pass: option closed at `{210.00 USD} @ 0.00 USD`, 100 SPY at `{477.90 USD}`, cash −48000.00, original link, no premium income; written after the yes |
| beancount-reconcile | 13 signed residual, unresolved | pass: ledger 4.00 above the statement, no assertion, no invented adjustment |

The importer-author miss predates this rewrite. Eval 5 expects the malformed
`PENDING` date row to be surfaced and its handling agreed before it is encoded.
The importer did surface it and got a green harness, but encoded "skip
`PENDING` rows" first and listed it afterwards as a decision to confirm. The
same eval against the suite as it stood before the rewrite (`1c5ac1b7a`)
behaved the same way, so the cause is the skill's Intake guidance, not the
rewrite.

## Not yet run

The same per-skill evals on Codex, which the milestone's definition of done
requires on both clients.
