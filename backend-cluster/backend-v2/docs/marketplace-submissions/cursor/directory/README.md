# Beancount.io hosted MCP connector

Canonical official registry identity: `io.beancount/beancount`.
Hosted endpoint: https://beancount.io/api-gateway/mcp
Source: https://github.com/bex-co/beancount-io
Connection guide: https://github.com/bex-co/beancount-io/blob/main/backend-cluster/backend-v2/docs/mcp.md

Install this MCP-only plugin, then authenticate through the client’s OAuth flow using a Beancount.io account. Choose the ledger access to grant. After authorization, ask the client to list your ledgers and run a read-only query against a synthetic QA ledger; preview proposed writes with dry_run before a separately authorized commit.

The configuration uses the server URL and OAuth discovery. It contains no API token, client secret, automatic tool approval, or local server process.

## Submission receipt — 2026-10-21 UTC

The manual form accepted the MCP-only submission. Its [Beancount.io result](https://cursor.directory/plugins/beancountio), observed at 21:51 UTC, states “Scanning your plugin…” and “This plugin is unpublished and hidden from the directory.” This is an accepted submission awaiting the platform security scan, not a public listing or a verified marketplace installation. Keep this receipt; do not resubmit while it is pending.

The submitted name is Beancount.io; homepage and repository are the canonical URLs above. Keywords are beancount, accounting, bookkeeping, mcp and oauth. The single MCP component is named `beancount`; its configuration is:

```json
{"mcpServers":{"beancount":{"url":"https://beancount.io/api-gateway/mcp"}}}
```

The result renders the intended per-server URL exactly. There is no command, args, environment credential, bundled skill or automatic approval. The form displayed no fee or agreement acceptance control, and the existing signed-in identity required no new access grant. The separate official Cursor application remains unsent pending Publisher Terms approval.

Before submission, the live catalog search for `beancount` exposed 50 links and no matching canonical identity, endpoint or repository. That bounded search is not an exhaustive absence claim. After the security scan, verify the public listing and native discovery-to-install path separately; reuse the scoped native-agent rehearsal only within its documented limits.
