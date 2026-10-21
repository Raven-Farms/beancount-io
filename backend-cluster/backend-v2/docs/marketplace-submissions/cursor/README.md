# Cursor marketplace preparation

This package contains one hosted MCP connection with URL-based OAuth discovery.
`official/` follows Cursor's `.cursor-plugin/plugin.json` and `mcp.json` format;
`directory/` supplies the separate `.mcp.json` detected by cursor.directory.
Neither package contains skills, a local server, API keys or automatic approvals.
The canonical registry identity remains `io.beancount/beancount`.

Checked 2026-10-21 UTC against the [official plugin reference](https://prod.cursor.com/docs/reference/plugins), [official template](https://github.com/cursor/plugin-template) and [community submission instructions](https://github.com/cursor/community-plugins#submit-a-plugin).
The repository-root `.cursor-plugin/marketplace.json` indexes the nested official
package using Cursor's supported multi-plugin layout. The unmodified official
template validator passes against both a fresh fixture and this repository; its
only warning is the absence of hooks, which this MCP-only package does not use.
The index contains one MCP-only plugin and does not publish the development or
customer skill trees. Format validation does not establish marketplace acceptance.

## Separate publication records

| Destination | State / next action |
| --- | --- |
| [Official Cursor](https://cursor.com/marketplace/publish) | Publisher identity sign-in succeeded. Application is prepared but unsent; final Submit Application explicitly agrees to [Publisher Terms](https://cursor.com/marketplace-publisher-terms) and requires the operator’s action-time approval. The root index now supplies the supported nested-package layout; actual intake and review remain unverified. |
| [cursor.directory](https://cursor.directory/plugins/new?type=mcp_server) | The [Beancount.io listing](https://cursor.directory/plugins/beancountio) clears its scan/hidden banners by 21:54 UTC and appears first under the directory’s New sort. Add to Cursor opens the correct native review and installs the URL-only User entry; new native OAuth is awaiting approval. [Dated receipt and limits](./directory/README.md#scan-and-native-install-follow-through--2026-10-21-utc). No duplicate submission or data PR is needed. |

Cursor IDE 3.24.18 is now installed from the official vendor download after disk
image, code-signature and Gatekeeper checks. Its separate, fresh QA profile opens
the workbench and accepts the actual community install link; an IDE agent conversation has not been verified. Existing
w1/m34/t003 retains ownership of that unfinished IDE journey.

The native Cursor Agent companion loaded the actual local plugin, completed
OAuth and performed a synthetic query plus one `dry_run: true` preview against
the canonical endpoint. The [dated rehearsal](./native-rehearsal-20261021.md)
records the client versions, scope narrowing, observed results and verification
limits. This is local native-agent compatibility evidence, not a marketplace
installation or publication receipt. Keep account identifiers and credentials
outside these public files.
