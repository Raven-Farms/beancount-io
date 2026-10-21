# GitHub and VS Code discovery preparation

Checked 2026-10-21 UTC. [GitHub's documented inclusion route](https://github.blog/ai-and-ml/generative-ai/how-to-find-install-and-manage-mcp-servers-with-the-github-mcp-registry/) asks publishers with an existing official-registry record to contact `partnerships@github.com`.
`nomination-email.md` is a concrete public-safe request for an authorized
operator to send; it has not been sent and no external review has started.
Do not publish a duplicate official-registry namespace or package.

| Surface | Observed state |
| --- | --- |
| Official MCP Registry | `io.beancount/beancount` version 1.0.0 is public and names the canonical hosted URL. |
| Curated GitHub MCP Registry | Live [Beancount search](https://github.com/mcp?search=beancount) returned no MCPs. Inclusion request remains unsent. |
| Native VS Code gallery | Unverified. VS Code 1.135.0 is installed, but the actual gallery search/install and authenticated Copilot journey have not run. Existing w1/m34/t003 retains native sign-in/fallback-port rehearsal ownership. |

[VS Code's current discovery guide](https://code.visualstudio.com/docs/agent-customization/mcp-servers#find-another-server) documents gallery search with `@mcp` and Browse MCP Servers. After curated inclusion, check the native Beancount result, install from that actual entry, and complete the shared synthetic QA OAuth/query/preview rehearsal. Record client version, listing/feed URL, date and deployment revision availability.

`mcp.json` is a prepared direct HTTP configuration for a VS Code workspace's
`.vscode/mcp.json`. It is a distinct manual fallback and does not create or prove
a gallery listing. It contains no token and relies on the client's OAuth flow.
Use [the MCP guide](../../mcp.md) and the [reviewer rehearsal](../../mcp-marketplaces.md#reviewer-rehearsal); do not authorize an unrelated browser account or production ledger for this test.
