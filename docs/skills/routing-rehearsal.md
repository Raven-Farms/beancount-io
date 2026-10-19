# Skill routing rehearsal

This record covers real Claude Code and Codex sessions choosing a skill for each
prompt in the suite routing set ([`evals/routing.json`](../../scripts/skills/routing.json)).
It is separate from the deterministic checks: `scripts/ci-check.py` validates
the set itself, and no client runs in CI. Every prompt and the ledger are
synthetic, and no hosted ledger was used.

## Method

- Runner: [`scripts/run-routing.py`](../../scripts/skills/run-routing.py). Each client
  gets a scratch Git repository in the system temp directory, outside this
  repository, with a small synthetic ledger and every `beancount-*` skill linked
  into `.claude/skills` and `.agents/skills`, as the installer links them.
- Claude Code: `claude -p --output-format stream-json --strict-mcp-config`, with
  Edit/Write disallowed. The choice is the first `Skill` tool call.
- Codex: `codex exec --json --sandbox read-only`. Codex has no skill tool, so
  the choice is the first command that names `<skill>/SKILL.md` and prints that
  skill's `name:` frontmatter. The client stops at its first choice; a session
  that ends without one chose no skill.
- A skill outside the suite counts as `none`. Each client's own user-level
  skills still load, as they would for a customer. On this machine that
  includes `dont-code-but-answer`, which Codex chose for the `bea ask` question.
- Each prompt runs once per run. Codex results vary between runs, so the
  baseline is two runs.

Reproduce with `python3 scripts/skills/run-routing.py --codex-model <model>`.
Results land in `scripts/skills/tmp/routing/<UTC stamp>/` (gitignored).

## Baseline — 2026-10-18

- Revision `bd8106f8f` (descriptions as of `4554ba440`). macOS 26.5.1, arm64.
- Claude Code 2.1.289 (`claude-opus-5-5`, the client default). Codex CLI
  0.163.0 with `gpt-6-luna`. The configured Codex default model is rejected for
  this ChatGPT account, so the runs pass `--codex-model gpt-6-luna`.
- Two full runs: 2026-10-18T23:57Z and 2026-10-19T00:00Z UTC.

| Client | Run 1 | Run 2 |
| --- | --- | --- |
| Claude Code | 47/48 | 47/48 |
| Codex | 43/48 | 45/48 |

Every misroute:

| Prompt id | Expected | Claude Code | Codex |
| --- | --- | --- | --- |
| `none-hosted-reconcile` | none | beancount-reconcile (both runs) | beancount-reconcile (both runs) |
| `none-hosted-dining-spend` | none | correct | beancount-ask (both runs) |
| `none-hosted-close-month` | none | correct | beancount-close (both runs) |
| `none-operating-currency-option` | none | correct | beancount-import (run 1 only) |
| `author-schwab-importer` | beancount-importer-author | correct | none (run 1 only) |

What the baseline shows:

- **Hosted ledgers are the consistent failure.** Five of the six hosted-prompt
  results across both clients picked a local skill. No description says the
  skills work only on local files, and Codex read the local skill in every
  run.
- **The name collisions the review predicted did not misroute here.** In both
  runs on both clients, closing one account (`close` directive), ledger
  `option` settings and options education, `bea ask` and documentation
  questions, and single manual entries all route to no suite skill. The one
  `option` miss went to `beancount-import`, not to `beancount-options`.
- **Codex has run-to-run noise.** Each single-run miss is one result out of
  two.

The first attempt at this baseline counted any Codex command naming a
`SKILL.md` as a choice, including searches for a guessed sibling path. It
reported misses that did not reproduce, so it was discarded, and the detector
now requires the skill's frontmatter in the command output.

## After description changes — 2026-10-19

- Revision `780c8094d`: the skip clauses and phrasings of `41d8298f2`, and
  the local-only scope and hosted-ledger hand-off of `780c8094d`. Same
  machine, clients, and models as the baseline.
- Two full runs: 2026-10-19T00:21Z and 00:25Z UTC.

| Client | Baseline runs | After runs |
| --- | --- | --- |
| Claude Code | 47/48, 47/48 | 48/48, 48/48 |
| Codex | 43/48, 45/48 | 47/48, 46/48 |

Fixed in both after runs: `none-hosted-reconcile` on Claude Code;
`none-hosted-dining-spend`, `none-operating-currency-option`, and
`author-schwab-importer` on Codex.

Remaining Codex misses, each in one of the two runs:

| Prompt id | Expected | Codex chose | Cause |
| --- | --- | --- | --- |
| `none-hosted-close-month` | none | beancount-close | Codex opens the local skill, which then hands the hosted ledger off (below). |
| `none-hosted-reconcile` | none | beancount-reconcile | Same. |
| `migrate-new-ledger-from-monarch` | beancount-migrate | beancount-init | One command opened `beancount-init` and then `beancount-migrate`, the skill it composes. The runner now records every skill such a command opens and scores the expected one among them, so this is not a regression. |

Three more Codex runs of these four prompts, after the scoring change: the
migration prompt routed 3/3, and the hosted prompts routed to no suite skill
in 6 of 9 results. Followed to the end, a Codex session that opened
`beancount-reconcile` for "My books live on Beancount.io (MCP connected)"
replied that the skill excludes hosted ledgers. With no Beancount.io tools in
the session, it asked the user to reconnect the MCP server and did not use
the local synthetic ledger. Opening a skill to read its scope counts as a miss
here, but the outcome is the hand-off the skill prescribes.

No prompt that routed correctly in both baseline runs misroutes in the after
runs on either client.

## Proposed renames — 2026-10-19

A scratch copy of the suite at `434d05084` renamed `beancount-options` →
`beancount-options-trades`, `beancount-close` → `beancount-close-month`, and
`beancount-ask` → `beancount-query` (directories, `name:`, and cross-references;
the persisted `;; beancount-options config` header unchanged), with the routing
set relabeled to match. Two runs per client, 2026-10-19T01:05Z and 01:09Z UTC,
compared with the two after runs above under the current names:

| Prompt group | Claude Code, current → renamed | Codex, current → renamed |
| --- | --- | --- |
| `close`/`option` collisions (7) | 7/7, 7/7 → 7/7, 7/7 | 7/7, 7/7 → 7/7, 7/7 |
| close and options positives (6) | 6/6, 6/6 → 6/6, 6/6 | 6/6, 6/6 → 6/6, 6/6 |
| ask/query positives (5) | 5/5, 5/5 → 5/5, 5/5 | 5/5, 5/5 → 5/5, 5/5 |
| ask/query near-misses (4) | 4/4, 4/4 → 4/4, 4/4 | 4/4, 4/4 → 4/4, 4/4 |
| all 48 | 48, 48 → 48, 48 | 47, 46 → 44, 46 |

The new names change nothing measurable for the prompts they were meant to
help: every collision prompt already routes correctly under the current names
on both clients. Codex's lower renamed total comes from prompts unrelated to
the renamed skills (`reconcile-one-account-june` → none and
`none-dinner-on-amex` → beancount-import, one run each, plus the known hosted
prompts), which is within its run-to-run variation. A rename would therefore be
for readability in `/` menus and catalogs, not for routing.

## Draft `beancount-add` — 2026-10-19

A scratch copy of the suite at `1ef07d812` plus a draft `beancount-add`
(description only), with the routing set extended to 53 prompts: the five
manual-entry prompts that were `none` (a dinner, rent, opening an account,
and closing one account two ways) relabeled to `beancount-add`, four new
positives (a transfer, a split receipt, a price, a paycheck), one hosted
near-miss, and `beancount-add` added as a confusable sibling of an import, an
options, a reconcile, a close, and an edit prompt. Two runs per client,
2026-10-19 UTC.

| Client | Run 1 | Run 2 |
| --- | --- | --- |
| Claude Code | 53/53 | 53/53 |
| Codex | 53/53 | 52/53 (`none-hosted-reconcile`, the known hosted miss) |

Every manual-entry prompt routed to the draft on both clients, including
both `close`-directive prompts, and no sibling lost a prompt it owned.

## `beancount-add` description after its evals — 2026-10-19

The eval round added "it never changes existing entries" to the description.
Two runs per client against the live suite: Claude Code 53/53 twice (draft:
53/53 twice); Codex 52/53 and 51/53 (draft: 53/53 and 52/53). Codex's new
single-run misses, `none-what-is-bea-ask` → beancount-ask and
`author-ally-headers-broke` → none, are unrelated to this skill and routed
correctly in four further Codex runs each; the third miss is the known
`none-hosted-reconcile`.

## Sibling hand-offs to `beancount-add` — 2026-10-19

The import, reconcile, options, ask, and close descriptions now name
`beancount-add` for single entries; ask also skips option pricing and greeks.
Claude Code routed 53/53 in both final runs. Codex routed 51/53 in the first
(`none-what-is-bea-ask` and `none-hosted-close-month`, both seen before). The
second Codex run stopped at the account's usage limit after 45 prompts, with
only the known `migrate-new-ledger-from-monarch` and `none-hosted-reconcile`
misses among them. In targeted Codex reruns, `none-what-is-bea-ask` and
`none-fix-payee-typo` routed correctly 4/4. `none-options-greeks` opened
`beancount-ask` in three of nine runs across the hand-off change and the
ask skip clause that followed, against none in ten earlier runs, so it is
recorded as Codex-variable rather than settled.
