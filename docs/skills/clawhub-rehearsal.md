# ClawHub publication and host rehearsal

Checked on macOS on 2026-10-19 PDT and updated on 2026-10-20 PDT. This records registry submission, public installation, real agent queries, and the remaining host limits separately.

## Release

[Publish run 39372550698](https://github.com/bex-co/beancount-io/actions/runs/39372550698) validates and submits all eleven customer bundles from main `b5f849059644d5a6171606850ea857d374abf059`, using ClawHub CLI 0.23.3 and publisher `puncsky`. Each submission returns version **1.0.0** with a version ID and publication-attempt ID. The workflow and its credential-removal step both succeed.

Every submission initially returns `pending-publication`. Workflow success means the upload was accepted; public availability is checked independently below. No duplicate submission, force install, scanner override, or source rewrite was used to make a release appear ready.

## Install results

Fresh OpenClaw state/workspace directories and fresh `HERMES_HOME` directories were created under gitignored package scratch space. A standalone ask install was checked before attempting the rest of the suite. Versions: **OpenClaw 2026.10.5** (`1b58cb9`), **Hermes v0.22.2** (`d923a5eb487a17c0a68801bba9ef0f56c81040a8`), **Python 3.14.3** for Hermes.

| Skill | Submitted version | OpenClaw | Hermes |
| --- | --- | --- | --- |
| beancount-add | 1.0.0 | Installed; audit Review | Installed; SAFE |
| beancount-ask | 1.0.0 | Installed; audit Safe | Installed; SAFE |
| beancount-close | 1.0.0 | Installed; audit Safe | Installed; SAFE |
| beancount-import | 1.0.0 | Installed; audit Safe | Installed; SAFE |
| beancount-importer-author | 1.0.0 | Installed; audit Review | Installed; SAFE |
| beancount-init | 1.0.0 | Installed; audit Review | Blocked; DANGEROUS |
| beancount-migrate | 1.0.0 | Installed; audit Review | Installed; SAFE |
| beancount-options | 1.0.0 | Installed after promotion; audit Review | Installed after promotion; SAFE |
| beancount-property | 1.0.0 | Installed after promotion; audit Review | Installed after promotion; SAFE |
| beancount-reconcile | 1.0.0 | Installed after promotion; audit Safe | Installed; SAFE |
| beancount-trade | 1.0.0 | Installed; audit Review | Installed; SAFE |

OpenClaw prints the registry's audit and allows both Safe and Review outcomes under its default policy. Review is not reported here as a clean audit. Every successful installed folder contains the byte-identical canonical `skills/LICENSE` and its own `references/bea-cli.md`; the single ask install therefore has no dependency on an installed init folder. Hermes adds its registry metadata file to the eight authored bundle files for ask.

The commands exercised are:

```sh
openclaw skills install @puncsky/beancount-ask
hermes skills install clawhub/@puncsky/beancount-ask --yes
openclaw skills update --all
hermes skills update
```

The same install commands were attempted once per suite skill, with isolated host state and the respective skill name. OpenClaw's update reports ask already at 1.0.0; Hermes reports no updates. A failed early ask/reconcile install was repeated only after public availability changed, and then succeeded.

Hermes's full registry init bundle is quarantined and rejected by `skills-guard-v10`: 18 findings, including the critical `agent_config_mod` rules for creating the ledger's `AGENTS.md` in `SKILL.md:188` and `references/agents-template.md:9`. This is the intended consent-gated workflow, retained by the release decision. The actual CLI exits 1 and does not install init. No override was attempted.

## Registry verification and promotion

At the 05:18 UTC check, options and property remain unavailable on the public API. Authenticated owner moderation diagnostics for each report `verdict: clean`, `isSuspicious: false`, `isMalwareBlocked: false`, and `legacyReason: pending.publication`. These are pending first submissions, not missing uploads; do not publish them again to clear the wait. The registry must finish publication before their public installs can be repeated.

**Update by 05:35 UTC:** options has become publicly available at 1.0.0. Its native OpenClaw install succeeds with an audit Review outcome; Hermes installs the same public bundle with a SAFE verdict and no force. Both installed folders carry the canonical license and local CLI contract. This brings the verified totals to **ten OpenClaw / nine Hermes**. Property remains unavailable on the subsequent public API check; only its existing first submission is still pending. No new release was uploaded to obtain this promotion.

**Final publication result:** property subsequently becomes public at 1.0.0. Its audit reports Review because the scanner sees a difference between the local-ledger scope and the conditional hosted/MCP handoff. Native OpenClaw installs it under the default policy, and Hermes installs it with a SAFE verdict at 05:41 UTC. The complete eleven-skill suite then installs together in the original OpenClaw suite workspace. Final totals are **eleven OpenClaw / ten Hermes**, with only Hermes init rejected. All eleven listings are public; no publication submission remains pending. Licenses and local CLI contracts are verified in every successful install, and no force or duplicate publish was used.

[Complete skills CI on `dec916039`](https://github.com/bex-co/beancount-io/actions/runs/39374976210) passes, including installer/first-query tests, the published-minimum CLI recipes, and QA-helper tests. That CI coverage is separate from the real OpenClaw/Hermes model-backed turns still pending below.

The strict `/verify` API is also distinct from native installation policy. Its initial snapshot reports `card.missing` for the first seven visible skills, with `security.status_not_clean` on Review outcomes; it does not establish a passing strict verification envelope. The native install successes above are actual client results, not inferred from that envelope. No clean cryptographic/card verification is claimed.

## Hermes search discovery

In the 2026-10-19 rehearsal, after every listing is public, `hermes skills search beancount --source clawhub --json --limit 30` returns no results in the fresh profile. Searching with `--source all` returns three older ClawHub entries, none from this suite. A direct control request to [ClawHub's search API](https://clawhub.ai/api/v1/search?q=beancount&limit=30) returns fourteen results, including all eleven `puncsky` skills. The explicit owner-qualified installs above succeed.

Source inspection distinguishes this from an unpublished skill: Hermes's [source-filtered adapter](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/tools/skills_hub_clawhub.py) walks the catalog before its lightweight fallback, while the [unfiltered router](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/tools/skills_hub_search.py) can answer from the centralized index without querying the live sources when that index has matches. This suggests a host catalog/index gap; it does not prove which cache or timeout is responsible. No local host-source patch, fabricated cache, or upstream issue was used to change the result. Recheck search after the host/index is updated; use explicit publisher-qualified installs meanwhile.

**Update 2026-10-20:** in a new isolated profile, the exact default command `hermes skills search beancount` now returns fourteen entries including all eleven suite skills. `hermes skills search beancount --source all --json --limit 30` confirms the complete set. The source-filtered command above still returns `[]`, while the registry control still includes all eleven. Default discovery has recovered; the narrower source-filtered gap remains tracked in [w6/040](../../.pm/w6/blocked/040.md). No host or cache patch was applied.

## First-query control and host acceptance

Installed the published **beancount-io 0.3.1** in a separate venv. The machine's existing `bea` reports 0.1.0, so it was not used for the control. Against the public synthetic `beancount-ask/evals/files/eval1_ledger.beancount` fixture, the [first-query guide](first-query.md)'s exact BQL returns:

| Account | June 2026 |
| --- | --- |
| Expenses:Food:Groceries | 141.60 USD |
| Expenses:Transport:Gas | 50.00 USD |
| Expenses:Entertainment:Streaming | 17.99 USD |

The fixture checksum remains unchanged. This is a direct CLI control, not an agent answer. During the initial installation rehearsal no model credential was configured in the fresh host profiles, and no credential was imported.

### Real host turns — 2026-10-20

The operator authorized temporary reuse of the existing Codex login. OpenClaw's official `@openclaw/codex@2026.10.5` plugin and selective `migrate apply codex --include-secrets --item auth:openai --yes` path imported only the credential item into isolated host state (one migrated item, 58 skipped). Hermes's `model` flow offered the existing CLI login, and its import prompt was accepted. No new OAuth grant or provider key was created. The original login file was byte-identical at cleanup; both temporary host profiles and their credential copies were deleted after testing.

Both hosts freshly installed `@puncsky/beancount-ask@1.0.0` from ClawHub on its own. OpenClaw reported Safe; Hermes reported SAFE and allowed installation without force. Each host received the first-query question, a request to use the installed skill and show its executed command, and explicit read-only/synthetic-data constraints.

| Host | Tested model and runtime | Observed result |
| --- | --- | --- |
| OpenClaw 2026.10.5 | `openai/gpt-6.1-sol`, explicitly selected OpenClaw embedded runtime, low reasoning | Loaded the installed skill and its bundled CLI contract, executed `bea` 0.3.1 through its tool bridge, and returned all three expected amounts. Exit 0; twelve tool calls, zero tool failures. |
| Hermes v0.22.2 | `gpt-6.1-sol`, `openai-codex` provider, low reasoning; `--skills beancount-ask`, `--toolsets terminal,file,skills` | Loaded the installed skill references, checked the actual CLI version, executed the query through `terminal`, and returned all three expected amounts. Exit 0. |

The executed query in each host was:

```sh
bea --file "$ledger" --json --no-input query "SELECT account, sum(weight) as total WHERE account ~ '^Expenses:' AND date >= 2026-06-01 AND date < 2026-07-01 GROUP BY account ORDER BY total DESC"
```

`$ledger` represents the absolute synthetic fixture path in that host's workspace. Both actual tool results contain the three rows above with `truncated: false`; the final answers show the executed command. Transfers and credit-card payments are excluded. Both ledger files retain SHA-256 `0676a52a1aaa8e80134a5a9aaf3b5fb659880732144a477d376c8b1e735322b6`.

OpenClaw's initial default Codex-harness attempt stopped before inference with `Codex native skill discovery returned errors`. A read-only native discovery probe identified an unrelated installed skill outside this worktree that lacks a description. That attempt is not counted as successful. The successful run explicitly used the [documented embedded runtime](https://docs.openclaw.ai/providers/openai/runtimes), with `agents.defaults.models["openai/gpt-6.1-sol"].agentRuntime.id` set to `openclaw`. It made a real authenticated model turn; neither the host nor skill source was patched. The skill optionally checked the absent sibling contract, then loaded its own bundled copy successfully.

The installation and first-query rehearsal is complete under t008's provision for recording compatibility gaps with follow-ups. Hermes init remains unsupported under the retained workflow ([w6/039](../../.pm/w6/blocked/039.md)); source-filtered search remains incomplete ([w6/040](../../.pm/w6/blocked/040.md)). Default Hermes search, standalone installs and real queries are verified. These results do not claim complete Hermes suite support or successful default Codex-harness execution.

## Suite 0.3.2 synchronization — 2026-10-20

While the closing checks ran, the independent wording audit `214ca2403` updated customer instructions and advanced the plugin suite to 0.3.2. Comparing current bundles with the actual installed 1.0.0 files identified five affected bundles: add, import, init, migrate and reconcile. The latter two inherit changed shared references. Ask and its first-query inputs are unchanged.

[Run 39393132904](https://github.com/bex-co/beancount-io/actions/runs/39393132904) from main `db23c44f171dd2cd25179d07c122b7500b8c51a3` dry-runs the suite and submits those five bundles as **1.0.1**. It skips the other six unchanged bundles at 1.0.0. Both jobs and publisher-credential cleanup succeed. [Complete skills CI on that commit](https://github.com/bex-co/beancount-io/actions/runs/39393084630) also passes.

All five new receipts report `pending-publication`; the initial post-run public API still exposes 1.0.0 as latest. This is accepted submission, not completed promotion. No duplicate release or force install was attempted. The first eleven 1.0.0 listings remain available.

**Subsequent promotion:** reconcile 1.0.1 becomes public. Its public download matches all nine current authored files, and its real OpenClaw install succeeds without force in the same fresh workspace as the six unchanged skills. Add, import, init and migrate still expose 1.0.0 as public latest at the final check. Their submitted updates remain the publication blocker.

The current 0.3.2 bundles were independently rechecked with the pinned Hermes `skills-guard-v10`: ten SAFE/allowed, init DANGEROUS/rejected with its same 18 findings. Fresh install-only profiles also install the six unchanged registry skills in both hosts without force; every installed authored file matches the current corresponding bundle. These are not installation results for the five unavailable 1.0.1 releases. Earlier complete 1.0.0 installation results and real ask queries remain valid.

The bundle/workflow/checker regressions pass: 130 full installer/recipe/journey tests, 43 focused checks, and six deliberate mutations caught (missing license/reference closure, metadata overwrite/indentation, omitted dry-run flag and skipped workflow build). No customer descriptions changed. Temporary install profiles and vendor runtimes were removed after evidence was retained.

**Review completed by 18:23 UTC:** all five 1.0.1 updates are public. Anonymous downloads of the eleven latest listings match all 105 authored files from the submitted release. The complete native OpenClaw workspace now contains those versions, with every authored file verified against the release bundles. No duplicate publication was needed. Hermes's independent init and source-filtered-search limits stay in w6/039 and w6/040.

## Suite 0.3.3 synchronization — 2026-10-20

Two later main commits updated init's setup-catalog instructions (`05658177b`) and migration source-name grammar (`a1d67f466`). Every standalone bundle contains the shared dedup reference, so all eleven need a registry update. The suite advances to 0.3.3; descriptions and routing are unchanged.

The released `bea` 0.3.1 help does not list `--preset` or `--title`. Init now checks the installed command's help before using either, keeps the standard-chart recipe on 0.3.1, and adds a title only with a selected preset on a supporting CLI. No CLI dependency or engine was upgraded for this change. The native Hermes v0.22.2 community scanner still allows ten current bundles and rejects init with its retained 18 findings.

Fresh native Hermes installs of the promoted 0.3.2 release verify all ten supported skills byte-for-byte; init is rejected with the same documented policy verdict. Default search again finds fourteen entries including the full suite, while explicit `--source clawhub` returns `[]`. No force or model credentials were used.

Before the 0.3.3 synchronization: all 130 installer/recipe/journey tests, 37 checker tests, structural/fixture checks, the skill validator and agent-guidance checks pass. Two focused tests also pass against the published minimum bea 0.3.1 (historical init and empty managed-price reads). The existing price-status test now checks the checkout's empty `refused` field while preserving the published release's older shape. Temporary host profiles and vendor source were removed after retaining the install/scan evidence.
