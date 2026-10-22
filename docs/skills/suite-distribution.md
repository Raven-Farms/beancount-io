# Beancount.io suite distribution

One Beancount.io package carries the thirteen customer workflows, their original
skill names and their shared references. Claude Code and Codex retain their
existing [whole-suite plugin installs](installation.md#plugin-both-clients).
Subsequent ClawHub releases target **`@puncsky/beancount-io`** as a single
`bundle-plugin`; the existing thirteen individual listings remain available as
legacy releases. [m6](../../.pm/w6/done/m6/README.md) preserves their completed
verification; [m6.5](../../.pm/w6/m6.5/README.md) owns this transition.

## Release status — 2026-10-22 UTC

Suite **0.4.0** is prepared for its first protected publication. The real pinned
ClawHub CLI 0.23.3 accepts the anonymous preview: one bundle plugin, **53 files**,
including all thirteen skill instructions and their required references. This
preview is not a public installation result. Native `clawhub package validate`
also passes against OpenClaw 2026.10.5, with no hard errors or runtime execution.
Its P2 missing-`package.json` notice is retained: this content-only bundle
intentionally declares no npm dependency/runtime package. The publication and native
OpenClaw checks below remain open until that exact package becomes available.

The content-only package uses the existing portable `plugin.json`, a generated
`.claude-plugin/plugin.json`, and the registry-required `openclaw.plugin.json`.
OpenClaw's Claude bundle marker selects its bundle loader without a native
runtime entrypoint or dependencies. No hooks or MCP connections are added.
The version is the same version declared by the existing Claude Code/Codex
suite; no separate per-skill release numbering is needed for future releases.

## Publication and compatibility contract

The [protected workflow](../../.github/workflows/publish-clawhub.yml) builds from
`skills/beancount-*/`, excluding eval fixtures, hidden files and development
skills. Symlinked runtime content, missing shared references, manifest inventory
drift and inconsistent suite versions fail the build. The single root `LICENSE`
is copied from the canonical MIT-0 `skills/LICENSE`.

Relevant pull requests and main pushes preview one package without publisher
credentials. An explicit main dispatch uses the existing protected environment
and publisher `puncsky`. A public version is skipped only when every authored
file hash matches. A different artifact at that version requires a version bump;
ambiguous lookup failures stop publication. The CLI waits for definitive
publication, and its temporary credentials are removed even on failure. Retain a
pending attempt and inspect its result rather than uploading identical content.

The intended native OpenClaw entry is `clawhub:@puncsky/beancount-io`; installation,
discovery and update commands will be recorded here after their exact rehearsal.
The local-path prototype was refused by OpenClaw's normal source-trust prompt;
no `--force` was used to bypass that gate.

## Hermes admission limits

Hermes **v0.22.4**, official commit
`4d04303818b61bf3aa09278af48356315515965b`, supports portable Agent Plugins v1
packages through its native plugin installer. Two actual checks on the complete
suite retain concrete restrictions:

- `hermes plugins validate <suite> --json` parses the root portable manifest,
  then reports all thirteen skills' nested `metadata` values as incompatible
  with its string-value metadata contract. These are the existing host
  declarations, preserved byte-for-byte.
- A fresh native `hermes plugins install file://<fixture> --no-enable` refuses
  the exact complete suite under its default `plugin-guard-v11` policy:
  **DANGEROUS, 20 findings**. Validation also identifies the intended init
  instruction-file writes. No plugin is installed or enabled, no scan setting
  is changed, and no forced install is attempted.

The fixture is a local Git repository of the generated suite, so this tests the
native installer and its policy on the package bytes, not public ClawHub plugin
ingestion. Hermes does not establish that registry route in this rehearsal.
The [existing standalone results](clawhub-rehearsal.md#final-current-version-verification--2026-10-22-utc)
remain valid for twelve supported skills; init's policy restriction remains
[w6/039](../../.pm/w6/blocked/039.md). Full Hermes suite admission awaits a
compatible metadata contract and a policy path that permits the approved init
workflow without weakening scanning or removing workflows.

## Legacy installs and migration

Existing individual registry records, versions and user files are retained.
Do not place the suite over manually edited standalone skills or remove them
automatically. Migration and name-precedence checks remain open until the
published suite can be installed natively. Users staying on individual releases
can keep the [previous exercised commands](installation.md#legacy-standalone-releases),
with their recorded host limits; future routine publication uses the suite.

## Primary contracts

- [ClawHub publishing](https://github.com/openclaw/clawhub/blob/main/docs/publishing.md)
  and the pinned CLI's `package publish --help` support bundle-plugin publication.
- [OpenClaw plugin bundles](https://docs.openclaw.ai/plugins/bundles) describe
  supported content packs and native feature mapping; the installed 2026.10.5
  bundle detector recognizes the Claude marker before the metadata-only native
  marker when no package runtime extensions are present.
- [Hermes portable plugins](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/website/docs/developer-guide/plugins/index.md#portable-agent-plugins-v1-packages)
  describe its native install, enable, namespaced skill loading and update paths.
