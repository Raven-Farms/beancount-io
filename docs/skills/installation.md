# Install the Beancount skills

Install the thirteen `beancount-*` ledger skills for Claude Code, Codex, or both, from any directory. You keep one Git checkout of the skills and link it into each agent's skill directory. Updating the checkout updates every agent, and the helper script never touches skills it did not install. [OpenClaw and Hermes Agent](#openclaw-and-hermes-agent) use standalone ClawHub bundles, with the availability and host limits below.

Rehearsed on macOS with Claude Code and Codex (see [tested with](first-query.md#tested-with)). Linux uses the same commands but has not been rehearsed. Windows is not covered.

## Prerequisites

- Git and Python 3.
- [`bea`](../../cli/README.md) 0.3.1 or later (`brew install bex-co/tap/bea` or `uv tool install beancount-io`; `bea upgrade` updates an older one). The skills use it for checks, queries, and ledger writes.
- [Claude Code](https://code.claude.com/docs/en/skills) and/or [Codex](https://developers.openai.com/codex/skills).

## 1. Get the skills

Fetch only the `skills/` directory of this repository into a stable location:

```sh
SKILLS_SRC="${XDG_DATA_HOME:-$HOME/.local/share}/beancount-io"
git clone --depth 1 --filter=blob:none --sparse https://github.com/bex-co/beancount-io.git "$SKILLS_SRC"
git -C "$SKILLS_SRC" sparse-checkout set skills scripts/skills docs/skills
```

The checkout contains the customer suite only. The repository's development skills live elsewhere and are not fetched.

## 2. Link them into your agents

Pick the skill directory for each agent you use:

| Agent | Every ledger on this machine | One ledger workspace |
| ----- | ---------------------------- | -------------------- |
| Claude Code | `~/.claude/skills` | `<workspace>/.claude/skills` |
| Codex | `~/.agents/skills` | `<workspace>/.agents/skills` |

Then link the suite into those directories (omit the one you don't use):

```sh
SKILLS_SRC="${XDG_DATA_HOME:-$HOME/.local/share}/beancount-io"
python3 "$SKILLS_SRC/scripts/skills/beancount-skills.py" install ~/.claude/skills ~/.agents/skills
```

For each directory, `install` creates one link per skill (`beancount-ask -> $SKILLS_SRC/skills/beancount-ask`, and so on), prints the source revision, and runs `verify`. It leaves every other entry in the directory alone. Both agents follow symlinked skill folders.

Links for a single workspace are absolute paths on your machine. Keep them out of a shared ledger repository, for example by adding `.claude/skills/beancount-*` and `.agents/skills/beancount-*` to its `.gitignore`.

## 3. Confirm the agents see them

Check the files first. `verify` only reads, and it exits nonzero with one line per missing skill, supporting reference, or sibling workflow:

```sh
python3 "$SKILLS_SRC/scripts/skills/beancount-skills.py" verify ~/.claude/skills ~/.agents/skills
```

Then ask each agent from your ledger directory. Both should name the same thirteen skills listed in the [skills catalog](../../skills/README.md).

```sh
claude -p "List the names of the skills available to you that start with beancount-, one per line, nothing else."
codex exec --skip-git-repo-check "List the names of the skills available to you that start with beancount-, one per line, nothing else."
```

In an interactive session, Claude Code lists skills with `/skills` and runs one with `/beancount-ask`. In Codex, mention a skill as `$beancount-ask`. Both agents also pick a skill on their own when your request matches its description.

Next: get a first answer from a sample ledger with the [first-query walkthrough](first-query.md), then complete a synthetic month with the [first-month guide](first-month.md). The latter uses the same `bea` and includes [verified Claude Code and Codex rehearsals](first-month-rehearsal.md).

### When a skill does not appear

1. Run `verify` and fix what its `FAIL` lines name. `install` repairs missing links. A skill whose directory is incomplete needs its checkout restored (`git -C "$SKILLS_SRC" restore skills`).
2. Start a new agent session. A running session may not pick up newly added skill directories.
3. Check that no setting hides the skill. For Claude Code, look for a `skillOverrides` entry set to `"off"`. For Codex, look for a `[[skills.config]]` entry with `enabled = false` in `~/.codex/config.toml`.
4. For a single-workspace install, launch the agent inside that workspace. Codex reads `.agents/skills` from the working directory up to the Git repository root.
5. If `install` reported a conflict, see [Existing copies and name conflicts](#existing-copies-and-name-conflicts).

## Install from a standard channel instead

The checkout-and-link install above is one way in. The standard skill channels also carry the suite, because it lives at the conventional `skills/<name>/SKILL.md` layout. A channel install **copies** the thirteen skills into the agent's directory instead of linking a checkout, so there is no `verify` script afterwards: confirm with the client skill listing in step 3 and the [first-query walkthrough](first-query.md). Install the whole suite every time — the skills hand off to siblings and share one command contract. Each channel below was checked against the tool's current help (2026-10-19); the exact forms matter, for the reasons given.

### `npx skills` (skills.sh)

```sh
# every ledger on this machine (drop -g inside one ledger workspace)
npx skills add bex-co/beancount-io -g -a claude-code codex -y
npx skills update -g -y   # later updates
```

Do **not** add `--skill '*'` or `--all`: explicit all-skill selection also included this repository's internal development skills in the 1.5.18 rehearsal (2026-10-19). The no-flag form above selects the customer `beancount-*` suite. To remove: `npx skills remove -g` and select the installed `beancount-*` names (or pass them as arguments).

### `gh skill`

```sh
gh skill install bex-co/beancount-io --all --pin main --agent claude-code --scope user
gh skill install bex-co/beancount-io --all --pin main --agent codex --scope user
```

`--pin main` is required today, not decoration: without it, `gh` resolves this repository's *latest release* (a mobile-app tag from before the flat `skills/` layout) and reports "no standard skills found". Pinned skills are skipped by `gh skill update`, so update by re-running the install commands with `--force` added. There is no `gh skill remove`: run `gh skill list` to see the install directories, then delete the installed `beancount-*` folders from them.

### Plugin (both clients)

The suite also ships as one plugin, `beancount-io`, from this repository's marketplace manifests. Plugin skills are namespaced: invoke one as `/beancount-io:beancount-ask`, against `/beancount-ask` from a linked install (in Codex, `$beancount-io:beancount-ask`).

```sh
# Claude Code — fetch only the manifest and skills/, never the whole repo
claude plugin marketplace add bex-co/beancount-io --sparse .claude-plugin skills
claude plugin install beancount-io@beancount-io
claude plugin update beancount-io@beancount-io   # later updates
claude plugin uninstall beancount-io@beancount-io # remove
```

```sh
# Codex
codex plugin marketplace add bex-co/beancount-io --sparse .agents/plugins --sparse plugin.json --sparse skills
codex plugin add beancount-io@beancount-io
codex plugin marketplace upgrade beancount-io     # refresh, then re-run the add to update
codex plugin add beancount-io@beancount-io
codex plugin remove beancount-io@beancount-io     # remove
```

Both manifests carry one shared suite version; a client delivers a new copy only when that version changes, and every shipped skill change bumps it. Confirm with each client's skill listing (step 3): the thirteen skills appear under the `beancount-io:` namespace.

### Hermes and raw GitHub folders

Hermes supports the direct GitHub skill path, but a single raw folder can omit the shared references its instructions read. A direct `beancount-ask` install was SAFE yet lacked its CLI contract. Use the self-contained [ClawHub bundle](#openclaw-and-hermes-agent) for a standalone install. Hermes v0.22.2 still rejects `beancount-init`'s intended creation of a new ledger's instruction files; that restriction does not prevent a bundled `beancount-ask` from working independently. The accidental import scanner finding and the shell installer example from the earlier rehearsal are fixed; no force install is needed for the currently verified non-init registry bundles. See the [dated results](clawhub-rehearsal.md).

### Choosing a method

- **Link installer (steps 1–3):** one checkout shared by both agents, updated by one `git pull`, with `verify` and conflict detection. Best default, and the only method that keeps local skill edits in Git.
- **Plugin:** the client's own managed install — marketplace discovery, namespaced skills, versioned updates. Best when you do not want to keep a checkout and do not edit skills.
- **A channel (`npx`/`gh`):** one command, no checkout to keep. You trade `verify` and the single update point for per-agent copies that each channel updates its own way.

Keep **one method per client**. A client holding the suite twice (say, linked into `~/.claude/skills` and installed as the plugin) lists both copies with the same descriptions; which one answers a given request is the client's choice, not something either installer controls. `verify` prints a note (not a failure) when it can tell the plugin also provides the suite. Moving from a linked install to the plugin: `uninstall` the links (see [Remove](#remove), keep the checkout only if you want it), then install the plugin.

### Switching methods

Remove the old install **before** installing by another method — two copies of one skill name leave the agent choosing between duplicates, and the link installer refuses a name a copy already holds. Removal per method: link installer — `python3 "$SKILLS_SRC/scripts/skills/beancount-skills.py" uninstall <dirs>` (see [Remove](#remove)); `npx skills` — `remove` above; `gh skill` — delete the folders `gh skill list` shows; Hermes — `uninstall` per name. Then install by the new method and re-run step 3's listing.

## OpenClaw and Hermes Agent

The publisher is [`puncsky` on ClawHub](https://clawhub.ai/puncsky). Registry bundles include their shared command references and the MIT-0 license, so `beancount-ask` can be installed alone without cloning this repository. Workflows such as migration and close name the sibling skills they hand off to; install those separately when needed.

Install the host using its official [OpenClaw guide](https://docs.openclaw.ai/install) or [Hermes guide](https://hermes-agent.nousresearch.com/docs/getting-started/installation), keep `bea` 0.3.1 or later on `PATH`, and configure a model provider in that host before an agent conversation.

From your ledger workspace, install the verified read-only skill:

```sh
openclaw skills install @puncsky/beancount-ask
```

Or, in Hermes:

```sh
hermes skills install clawhub/@puncsky/beancount-ask --yes
```

Update the registry skills already installed in the selected host/workspace:

```sh
openclaw skills update --all
hermes skills update
```

These commands were run on macOS with OpenClaw 2026.10.5 and Hermes v0.22.2. Both installed the standalone `beancount-ask@1.0.0` with its CLI contract and license; Hermes's scanner allowed it without `--force`. On 2026-10-20, each host also completed the synthetic first query through the installed skill and an executed `bea` 0.3.1 command, with the expected figures and unchanged ledger checksum. The [registry rehearsal](clawhub-rehearsal.md#real-host-turns--2026-10-20) records the tested model/runtime configuration and its limits; OpenClaw used its explicitly selected embedded runtime.

**Release status, 2026-10-20:** all eleven original 1.0.0 releases are public. That eleven-skill release installs in one OpenClaw workspace. Ten skills install in Hermes; its scanner blocks `beancount-init` for the intended creation of ledger instruction files. Use the supported skills individually in Hermes, and keep the Git/link route above for the complete Claude Code/Codex suite. See the [per-skill results](clawhub-rehearsal.md#install-results).

The 0.3.2 wording fixes were verified as registry 1.0.1 for add, import, init, migrate and reconcile, with the other six listings at 1.0.0. All eleven downloads and OpenClaw installations matched that submitted release. Later main changes were submitted as suite 0.3.3: five registry 1.0.2 updates and six 1.0.1 updates. At the 2026-10-21 04:23 UTC check, all eleven updates are public and all 105 authored files match the submitted release, including close/options 1.0.1. See the [synchronization record](clawhub-rehearsal.md#suite-033-synchronization--2026-10-20) for release progress and host limits.

The Git/plugin suite now also contains `beancount-roll-forward` and `beancount-accruals`, bringing its inventory to thirteen. Their first registry releases, plus later add/ask/close/import/migrate/reconcile/trade changes, pass the client/adoption release gates and are accepted by protected run39679035375 as pending-publication. At21:41UTC on2026-10-21, the public registry still covers the original eleven skills and exposes older versions for the seven updates. The four unchanged current versions are publicly exact; install new versions only after promotion. Native Codex 0.163.0 works with configured `gpt-6.1-sol`, and Claude Code 2.1.306 resumes usable default-model turns on 2026-10-21. On the frozen 0.3.6 source, Claude discovers all thirteen skills and scores 113/113, with no new miss in that cohort. The subsequent0.3.7 description repairs use115 requests: Codex passes115/115 twice, while Claude resolves115/115 from114 original valid observations plus one documented-default timeout recovery. All earlier failures, including the historical PDF first-open loss, remain recorded. Current behavioral validation covers dated valuation, accrual recognition/identity, and reproducible variance commentary; the [dated client release record](client-release-controls-20261021.md) distinguishes source versions, corrections, actual results and remaining publication gates.

Suite 0.3.8 repairs local/hosted scope conflicts and requires a working validator
before an existing-ledger write. Its [native before/after controls](scope-contract-controls-20261022.md)
preserve the explicitly unvalidated init scaffold, approved developer-tool
writes and supported broker/migration flows. Descriptions and routing requests
are unchanged. Protected [run39708894097](https://github.com/bex-co/beancount-io/actions/runs/39708894097)
accepts all thirteen changed 1.0.4 submissions with exact fingerprints and clean
credential removal. By 02:49 UTC ten current versions/97 authored files are
public and install exactly in OpenClaw; Hermes allows nine versions/90 files
across its suite and separate import-recovery profile. Init retains its policy
refusal. Both hosts complete the standalone ask 1.0.4 first query through
published bea 0.3.1 with unchanged synthetic ledgers. The final 2026-10-22
follow-through clears the remaining accruals, property and reconcile promotions:
all thirteen latest versions are 1.0.4, and all thirteen OpenClaw installs match
119/119 authored files. Twelve supported Hermes installs match 112/112 files
across the suite and the documented import-recovery profile; init retains its
policy refusal. Fresh default Hermes search now displays all thirteen suite
identifiers among sixteen results. The [final verification](clawhub-rehearsal.md#final-current-version-verification--2026-10-22-utc)
preserves the original failures, recoveries, prior model-backed queries and
exact host limits. The owner selects a single suite package for future ClawHub
releases; that package is not yet published or verified by this milestone.
An upload receipt does not establish public availability or complete support.

The current Hermes default search finds all thirteen suite listings:

```sh
hermes skills search beancount
```

The earlier 2026-10-22 v0.22.4 cohort finds eleven names among fourteen results
with `--source all --json --limit 30`, but omits the newly public roll-forward
listing. That cohort's source-filtered `--source clawhub` path returned no results;
its separate follow-up remains open after this closeout's successful default search.
Use the explicit publisher-qualified identifiers for listings absent from
search; the [dated evidence](clawhub-rehearsal.md#current-version-follow-through--2026-10-22-0249-utc)
records discovery separately from version and installed-byte verification.

## Update

```sh
SKILLS_SRC="${XDG_DATA_HOME:-$HOME/.local/share}/beancount-io"
git -C "$SKILLS_SRC" status --short skills
git -C "$SKILLS_SRC" pull --ff-only
python3 "$SKILLS_SRC/scripts/skills/beancount-skills.py" install ~/.claude/skills ~/.agents/skills
```

The pull updates every linked agent at once. Running `install` again keeps existing links, links any skill added to the suite since your last install, and prints the revision you are now on (`source … at <commit> <date>`).

### Upgrading from the old layout

Installs made before 2026-10-19 link into the checkout's old `skills/.claude/skills/<name>` folders, and their sparse checkout fetches `skills` only. After a pull those links point at nothing, so the skills disappear from both agents without an error. Upgrade once, from Git:

<!-- upgrade -->
```sh
SKILLS_SRC="${XDG_DATA_HOME:-$HOME/.local/share}/beancount-io"
git -C "$SKILLS_SRC" pull --ff-only
git -C "$SKILLS_SRC" sparse-checkout set skills scripts/skills docs/skills
python3 "$SKILLS_SRC/scripts/skills/beancount-skills.py" install ~/.claude/skills ~/.agents/skills
```

`install` replaces each old link that points into this checkout with a link to `skills/<name>` (`relinked … (moved from skills/.claude/skills)`), then runs `verify`. A link into a different checkout is left alone and reported as a conflict. List your workspace skill directories too if you installed into any.

### Local edits

`status` shows any edits you made to the checkout, and `install` lists them too, because every linked agent uses them. `git pull --ff-only` keeps edits that the update does not touch. If the update changes a file you edited, Git stops with `Your local changes to the following files would be overwritten` and changes nothing. Then choose one:

```sh
git -C "$SKILLS_SRC" stash && git -C "$SKILLS_SRC" pull --ff-only && git -C "$SKILLS_SRC" stash pop   # keep your edits on top
git -C "$SKILLS_SRC" diff > ~/beancount-skills-edits.patch && git -C "$SKILLS_SRC" restore skills   # save them aside, take the update
```

### Existing copies and name conflicts

If a skill directory already holds a `beancount-*` entry that is not a link into this checkout, such as an earlier manual copy or a link to another checkout, `install` changes nothing in that directory. It prints a `CONFLICT` line for each entry, saying whether a copy is identical to the checkout or listing the files that differ. To keep an entry, move it out of the skill directory, then run `install` again. A renamed copy left inside the directory would still load as a second skill.

```sh
mkdir -p ~/beancount-skill-backups
mv ~/.claude/skills/beancount-ask ~/beancount-skill-backups/
```

## Remove

```sh
SKILLS_SRC="${XDG_DATA_HOME:-$HOME/.local/share}/beancount-io"
python3 "$SKILLS_SRC/scripts/skills/beancount-skills.py" uninstall ~/.claude/skills ~/.agents/skills
git -C "$SKILLS_SRC" status --short skills
rm -rf "$SKILLS_SRC"
```

`uninstall` removes only the links that point into this checkout. It reports anything else with a suite skill's name as kept, and it never touches other skills, agent settings, or ledgers. Check the `status` output for edits you want to keep before deleting the checkout.
