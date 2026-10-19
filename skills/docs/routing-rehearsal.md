# Skill routing rehearsal

This record covers real Claude Code and Codex sessions choosing a skill for each
prompt in the suite routing set ([`evals/routing.json`](../evals/routing.json)).
It is separate from the deterministic checks: `scripts/ci-check.py` validates
the set itself, and no client runs in CI. Every prompt and the ledger are
synthetic, and no hosted ledger was used.

## Method

- Runner: [`scripts/run-routing.py`](../scripts/run-routing.py). Each client
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

Reproduce with `python3 skills/scripts/run-routing.py --codex-model <model>`.
Results land in `skills/tmp/routing/<UTC stamp>/` (gitignored).

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
