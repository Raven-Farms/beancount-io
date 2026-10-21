# GitHub and VS Code discovery preparation

Checked 2026-10-21 UTC. [GitHub's documented inclusion route](https://github.blog/ai-and-ml/generative-ai/how-to-find-install-and-manage-mcp-servers-with-the-github-mcp-registry/) asks publishers with an existing official-registry record to contact `partnerships@github.com`.
`nomination-email.md` is a concrete public-safe request for an authorized
operator to send; it has not been sent and no external review has started.
Do not publish a duplicate official-registry namespace or package.

| Surface | Observed state |
| --- | --- |
| Official MCP Registry | `io.beancount/beancount` version 1.0.0 is public and names the canonical hosted URL. |
| Curated GitHub MCP Registry | Live [Beancount search](https://github.com/mcp?search=beancount) returned no MCPs. Inclusion request remains unsent. |
| Native VS Code gallery | The actual `@mcp` catalog reports 51 entries; 50 unique names were observed across overlapping viewports, with no Beancount match. This is not an exhaustive absence or name-filtered result. Installation and authenticated Copilot journey remain unverified; w1/m34/t003 retains shared rehearsal ownership. |

[VS Code's current discovery guide](https://code.visualstudio.com/docs/agent-customization/mcp-servers#find-another-server) documents gallery search with `@mcp` and Browse MCP Servers. After curated inclusion, check the native Beancount result, install from that actual entry, and complete the shared synthetic QA OAuth/query/preview rehearsal. Record client version, listing/feed URL, date and deployment revision availability.

`mcp.json` is a prepared direct HTTP configuration for a VS Code workspace's
`.vscode/mcp.json`. It is a distinct manual fallback and does not create or prove
a gallery listing. It contains no token and relies on the client's OAuth flow.
Use [the MCP guide](../../mcp.md) and the [reviewer rehearsal](../../mcp-marketplaces.md#reviewer-rehearsal); do not authorize an unrelated browser account or production ledger for this test.

## Native gallery observation — 2026-10-21 UTC

In VS Code **1.135.0**, a separate marketplace QA profile opens the real
Extensions panel. **Enable MCP Servers Marketplace → Enable**, followed by
**Filter Extensions → MCP Servers**, produces the `@mcp` query and a reported
51 entries at 19:17 UTC. Fifty unique visible names are collected across
overlapping scroll positions; none is Beancount. One reported entry is not
accounted for, so this does not establish exhaustive absence. No typed
Beancount name filter or direct registry-identity search is claimed.

The generic **Filter Extensions → Sort By → Name** menu later produces
`@mcp @sort:name` and **No MCP Servers found**. That unsupported-result
combination is not used as evidence of Beancount absence. Clearing the query
and choosing MCP Servers again restores `@mcp`. No server installation,
OAuth grant, accounting query or preview occurs. GitHub's inclusion request
remains unsent; native catalog observation does not imply curation acceptance.

Private accessibility snapshots, exact visible names and the sort observation
are retained under ignored
`backend-cluster/backend-v2/tmp/w6-cursor-client/`. This is separate evidence
from GitHub's web search and the existing official MCP Registry record.
