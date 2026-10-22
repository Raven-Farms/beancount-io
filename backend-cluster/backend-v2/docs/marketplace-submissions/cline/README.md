# Beancount.io for Cline

Connect Cline to a hosted Beancount.io ledger through Streamable HTTP and OAuth.
Canonical registry identity: `io.beancount/beancount`.

## Install and connect

1. In Cline 4.1.25, choose **Customize → MCP → Installed**. Choose **Add Remote
   Server**, or use **Edit Configuration** and merge the `mcpServers` entry from
   [`cline_mcp_settings.json`](./cline_mcp_settings.json) into your existing
   configuration. The URL uses Streamable HTTP; no local command or API key is
   needed. Keep `autoApprove` empty.
2. Use Cline's OAuth authentication action. Sign in to Beancount.io, check the
   requester/redirect identity on the consent page, and approve the intended
   ledger access. This client currently requests `openid offline_access
   ledger.read ledger.write ledger.admin`; the consent page selects a ledger
   but does not offer individual scope controls. Review that access before
   approving. For review, use only the dedicated QA account's synthetic ledger.
3. After the connection initializes, enumerate the live tools and resources,
   then run a read against the known synthetic fixture. Use the [shared
   reviewer rehearsal](../../mcp-marketplaces.md#reviewer-rehearsal) to verify a
   known answer and one tool-supported `dry_run` preview without changing data.

The setup controls and URL-only configuration were checked in the real
extension on 2026-10-21 UTC. Authenticated discovery, query and preview still
need completion; this is not a claim that the host journey is verified.
The [current client documentation](https://docs.cline.bot/mcp/mcp-overview) covers
MCP management.
The [MCP guide](../../mcp.md) explains scopes, credential boundaries, capabilities
and existing host evidence. Every user signs in separately. Never put a reviewer
password or token in a README, issue or directory listing, and do not enable
automatic approval of accounting writes.

## Submission preparation — 2026-10-21 UTC

[Current Cline requirements](https://github.com/cline/mcp-marketplace#how-to-submit-your-mcp-server) and its [issue template](https://github.com/cline/mcp-marketplace/blob/main/.github/ISSUE_TEMPLATE/mcp-server-submission.yml) accept a hosted server submission and require install testing from README/llms-install instructions plus a 400×400 PNG.
`logo-400.png` is a deterministic resize of the canonical public
`https://beancount.io/lgasset/logo.png` (256×256), without changing its design.
`submission.md` follows the current fields but deliberately leaves the required
installation/stability confirmations unchecked.

The public submission-issue search found no Beancount match. The exact public
catalog feed used by the tagged extension also has no match, as recorded below;
the blank native Marketplace panel does not prove what rendered there.
In VS Code 1.135.0, the signed official Cline 4.1.25
extension accepted this configuration and displayed **Authenticate**. The
official `cline@3.0.73` CLI independently completed discovery and dynamic client
registration, printed its authorization URL, and reached the real consent
page through a loopback callback. The dedicated QA browser session and intended
synthetic ledger are now available. No access grant was approved; the callback
expired while approval remained pending. Complete a fresh authorization,
authenticated discovery, known query, unchanged-state preview and real catalog
check before checking the template's claims or sending the issue. No issue,
live listing or successful Cline OAuth journey is represented by these files.

For isolated operator testing, note that a VS Code profile alone does not isolate
Cline state: this extension opened `~/.cline/data/settings/cline_mcp_settings.json`.
Back up and merge existing settings rather than replacing them. The rehearsal's
temporary extension entry was removed and the original file restored. CLI
testing used separate `CLINE_DIR`, `CLINE_DATA_DIR` and
`CLINE_MCP_SETTINGS_PATH` paths, with auto-update disabled. CLI 3.0.73 has no
supported per-server OAuth scope override. Any later model-driven rehearsal
must explicitly disable its default automatic tool approval.

## Native catalog feed control — 2026-10-21 UTC

Cline 4.1.25's [tagged marketplace helper](https://github.com/cline/cline/blob/01b8a9724da905423e636396d7fb4acdf47796bb/apps/vscode/src/core/controller/marketplace/marketplace-helpers.ts#L50)
uses the public [catalog feed](https://cline.github.io/marketplace/catalog.json).
At 07:26 UTC that exact feed returns HTTP 200 and 203 entries, including 149
MCP servers; its generation timestamp is 2026-09-18T20:15:28.359Z. Searching
every entry finds zero matches for `beancount`, `io.beancount/beancount`, the
canonical hosted endpoint or `bex-co/beancount-io`. Response SHA-256 is
`187ebe2b130e25f261a805cc5930a19e275ece2c34ab21bd9df966a566b9848c`.

This establishes the observed public feed's deduplication result, separately
from the native Marketplace panel, which appeared blank. It does not diagnose
that UI discrepancy or prove enterprise-filtered rendering. Native setup and
catalog preparation do not satisfy the unchecked authenticated installation,
query, preview or stability claims; no issue or listing was submitted.

## Renewed isolated CLI installation — 2026-10-22 UTC

The existing official Cline CLI reports3.0.73. In separate `CLINE_DIR`,
`CLINE_DATA_DIR` and `CLINE_MCP_SETTINGS_PATH` locations, its native
`mcp add <name> <url> --transport streamable-http --yes --json` command returns
exit0, status `installed` and no warnings for the canonical MCP endpoint.
Auto-update is disabled with `CLINE_NO_AUTO_UPDATE=1`; the task process does not
inherit model credentials. The original user settings checksum is unchanged.

Readback verifies exactly one task server. This CLI's managed settings nest
`type: streamableHttp` and `url` under a `transport` object; this is distinct
from the extension configuration above. Use the CLI's own installation command
for CLI-managed settings. The resulting task entry has only transport metadata,
with no credential fields. An initial generic evidence reader inspected flat
extension fields; the retained corrected record reads the actual nested shape.

This preparation does not approve OAuth, invoke a model, discover authenticated
tools or run a ledger query/preview. Browser control was unavailable in this
snapshot; the later native Hub observation below records its restoration. Complete
fresh native OAuth with the separately approved synthetic-ledger grant before
making authenticated-install or stability claims. The task settings remain
isolated and ready; existing user and Cursor configuration are untouched.

## Native Hub catalog observation — 2026-10-22 UTC

The official CLI 3.0.73 starts its supported `hub dashboard --no-open` with
the task's isolated config/data, workspace and credential-free MCP settings.
The real browser interface displays Hub version 0.0.95. Its Installed panel
shows the one enabled Streamable HTTP entry at the canonical hosted URL and
the task-owned settings path. The Marketplace view reports 149 MCP entries;
typing `beancount` in its actual name filter returns zero Marketplace matches,
while the installed task entry remains visible.

This is native Hub rendering and name-filter evidence. It does not replace the
earlier blank VS Code extension observation, prove another effective catalog,
or establish an authenticated connection. The inspected Installed view exposes
configuration/removal controls; the Tools view configures built-in/plugin tools.
Neither inspected view exposes MCP authentication or manual MCP execution.
No provider credentials are inherited, model session launched, access grant
approved or accounting query/preview performed. Any later model-assisted CLI
rehearsal must use its documented `--auto-approve false` option.

The prior browser-connection limitation is cleared for this observation. OAuth,
authenticated discovery/query/preview and the actual submission/review gates
remain open. Raw DOM and the rendered filter screenshot are retained under
ignored `backend-cluster/backend-v2/tmp/w6-native-20261022T0818/`.
