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

The public submission-issue search found no Beancount match; actual in-client
catalog dedup remains open. In VS Code 1.135.0, the signed official Cline 4.1.25
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
