# Beancount.io hosted MCP connector

Canonical official registry identity: `io.beancount/beancount`.
Hosted endpoint: https://beancount.io/api-gateway/mcp
Source: https://github.com/bex-co/beancount-io
Connection guide: https://github.com/bex-co/beancount-io/blob/main/backend-cluster/backend-v2/docs/mcp.md

Install this MCP-only plugin, then authenticate through the client’s OAuth flow using a Beancount.io account. Choose the ledger access to grant. After authorization, ask the client to list your ledgers and run a read-only query against a synthetic QA ledger; preview proposed writes with dry_run before a separately authorized commit.

The configuration uses the server URL and OAuth discovery. It contains no API token, client secret, automatic tool approval, or local server process.
