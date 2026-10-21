# Beancount.io for Cline

Connect Cline to a hosted Beancount.io ledger through Streamable HTTP and OAuth.
Canonical registry identity: `io.beancount/beancount`.

## Install and connect

1. In Cline's MCP Servers panel, open the Remote Servers view and choose to add
   a remote server. Select Streamable HTTP and enter
   `https://beancount.io/api-gateway/mcp`. Do not use `/mcp` or a local command.
2. Use Cline's OAuth authentication action. Sign in to Beancount.io, check the
   requester/redirect identity on the consent page, and approve the intended
   ledger access. For review, use the dedicated QA account and synthetic ledger.
3. After the connection initializes, enumerate the live tools and resources,
   then run a read against the known synthetic fixture. Use the [shared
   reviewer rehearsal](../../mcp-marketplaces.md#reviewer-rehearsal) to verify a
   known answer and one tool-supported `dry_run` preview without changing data.

Cline's actual controls and OAuth outcome still need a fresh native rehearsal;
these instructions are prepared from the [current client documentation](https://docs.cline.bot/mcp/mcp-overview), not a claim that this host is already verified.
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
catalog dedup remains open. VS Code 1.135.0 is installed, but no Cline extension
or configured Cline session was found in the inspected environment. Complete
native setup with the dedicated QA browser session, query and preview before
checking the template's claims or sending the issue. No issue, live listing or
successful Cline OAuth journey is represented by these files.
