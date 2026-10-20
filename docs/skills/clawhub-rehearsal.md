# ClawHub publication and host rehearsal

Checked on macOS on 2026-10-19 PDT (2026-10-20 UTC). This records registry submission, public installation, and the remaining host/query limits separately.

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

After every listing is public, `hermes skills search beancount --source clawhub --json --limit 30` returns no results in the fresh profile. Searching with `--source all` returns three older ClawHub entries, none from this suite. A direct control request to [ClawHub's search API](https://clawhub.ai/api/v1/search?q=beancount&limit=30) returns fourteen results, including all eleven `puncsky` skills. The explicit owner-qualified installs above succeed.

Source inspection distinguishes this from an unpublished skill: Hermes's [source-filtered adapter](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/tools/skills_hub_clawhub.py) walks the catalog before its lightweight fallback, while the [unfiltered router](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/tools/skills_hub_search.py) can answer from the centralized index without querying the live sources when that index has matches. This suggests a host catalog/index gap; it does not prove which cache or timeout is responsible. No local host-source patch, fabricated cache, or upstream issue was used to change the result. Recheck search after the host/index is updated; use explicit publisher-qualified installs meanwhile.

## First-query control and remaining acceptance

Installed the published **beancount-io 0.3.1** in a separate venv. The machine's existing `bea` reports 0.1.0, so it was not used for the control. Against the public synthetic `beancount-ask/evals/files/eval1_ledger.beancount` fixture, the [first-query guide](first-query.md)'s exact BQL returns:

| Account | June 2026 |
| --- | --- |
| Expenses:Food:Groceries | 141.60 USD |
| Expenses:Transport:Gas | 50.00 USD |
| Expenses:Entertainment:Streaming | 17.99 USD |

The fixture checksum remains unchanged. This is a direct CLI control, not an agent answer. No model credential is configured in the fresh host profiles. The checked `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `OPENROUTER_API_KEY` variables are absent from the process and the release operator's supplied environment. Temporary use of an existing model login is awaiting the operator's choice; no credential was imported during this rehearsal.

Remaining acceptance is Hermes search discovery, a compatible Hermes policy for init, and an actual model-backed first-query turn in each host. Publication task w6/m6/t007 is complete; this rehearsal does not yet establish complete cross-host workflow support or close w6/m6.
