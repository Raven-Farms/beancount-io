# Cursor marketplace preparation

This package contains one hosted MCP connection with URL-based OAuth discovery.
`official/` follows Cursor's `.cursor-plugin/plugin.json` and `mcp.json` format;
`directory/` supplies the separate `.mcp.json` detected by cursor.directory.
Neither package contains skills, a local server, API keys or automatic approvals.
The canonical registry identity remains `io.beancount/beancount`.

Checked 2026-10-21 UTC against the [official plugin reference](https://prod.cursor.com/docs/reference/plugins), [official template](https://github.com/cursor/plugin-template) and [community submission instructions](https://github.com/cursor/community-plugins#submit-a-plugin).
The official template validator passes in a temporary multi-plugin fixture; its
only warning is the absence of hooks, which this MCP-only package does not use.
That format check does not establish a native install or marketplace acceptance.

## Separate publication records

| Destination | State / next action |
| --- | --- |
| [Official Cursor](https://cursor.com/marketplace/publish) | Publisher identity sign-in succeeded. Application is prepared but unsent; final Submit Application explicitly agrees to [Publisher Terms](https://cursor.com/marketplace-publisher-terms) and requires the operator’s action-time approval. Confirm the supported repository/subdirectory submission flow before submitting this monorepo package. |
| [cursor.directory](https://cursor.directory/plugins/new?type=mcp_server) | Identity sign-in succeeded. Live form offers Auto (GitHub) scan or Manual name/description/repository/homepage/keywords/component content and Publish Plugin. No publication was sent; no data PR is assumed. Search the live catalog for the canonical endpoint/repository before submission. |

Cursor IDE is not installed in the inspected environment. The installed Cursor
Agent 2026.09.15-d2fe57e is a different distribution; its `plugin --help` advertises
marketplace management, not a `plugin validate` command or proof of native IDE
installation. Existing w1/m34/t003 retains the fresh Cursor OAuth/read/preview
rehearsal. A publisher login or schema check does not clear that prerequisite.

Once the account holder has the actual supported client and dedicated QA
session, install this package from a fresh configuration, follow [the shared
reviewer rehearsal](../../mcp-marketplaces.md#reviewer-rehearsal), and record the
synthetic query/unchanged-ledger preview before making any tested-install claim.
Keep account identifiers and credentials outside these public files.
