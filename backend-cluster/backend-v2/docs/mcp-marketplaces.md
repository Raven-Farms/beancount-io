# Hosted MCP marketplace submissions

Checked **2026-10-21 UTC**. This is the shared submission packet for w6/m8–m10,
041 and 042. A submission, registry import, or supported transport does not prove
a public listing or a successful sign-in. Recheck the target before submitting;
reuse an existing record instead of creating a duplicate.

## Canonical listing copy

Use [`../server.json`](../server.json) as the source for registry metadata.

| Field | Value |
| --- | --- |
| Name | Beancount.io |
| Registry name | `io.beancount/beancount` |
| Short description | Query, edit, and reconcile a hosted Beancount ledger: BQL, reports, files, and bank imports. |
| Endpoint | `https://beancount.io/api-gateway/mcp` |
| Transport | Streamable HTTP |
| Authentication | OAuth; sign in to Beancount.io and approve the requested ledger permissions. |
| Product | https://beancount.io/ |
| Source | https://github.com/bex-co/beancount-io/tree/main/backend-cluster/backend-v2 |
| Setup and authorization guide | https://github.com/bex-co/beancount-io/blob/main/backend-cluster/backend-v2/docs/mcp.md |
| Support | https://github.com/bex-co/beancount-io/issues |
| Icon | https://beancount.io/lgasset/logo.png (PNG; registry declares 256×256) |

Long description for forms:

> Connect an agent to a hosted Beancount.io ledger. Query transactions with BQL,
> read financial reports and ledger files, preview supported changes, and work
> with linked bank imports. Connect to the existing remote endpoint and sign in
> with OAuth. Access follows the signed-in person's ledger permissions and the
> approved scopes. This connector accesses hosted ledgers; it does not open a
> local ledger file on the agent's computer.

Use the version from `server.json` for the registry record. A repository commit
is not a deployed server version. Discover the actual tools, resources and
prompts from the authenticated service; do not copy a static capability count
into listings. Adapt an icon only when a directory requires another size.
Operator contact addresses and reviewer credentials are supplied privately by
the publisher account, never copied into this packet or public submissions.

## Target inventory

The publisher/operator owns account access, domain proofs and external review;
the repository worker owns artifacts and verification. “Unverified” below means
no reliable catalog result was obtained, rather than an assertion of absence.

| Target / owner task | Existing record and current evidence | Route, gate and next action |
| --- | --- | --- |
| Official MCP Registry / w2/m36 | Published as [`io.beancount/beancount`](https://registry.modelcontextprotocol.io/v0.1/servers/io.beancount%2Fbeancount/versions/latest). | Existing canonical record. Other directories' imports are checked separately. |
| Smithery / m8/t002 | No matching hosted record confirmed by public search or qualified API lookup; candidate HTML says server not found. | [Lifecycle notice](https://smithery.ai/future): proxy, accounts, API and CLI stop October 31, 2026; a curated directory with direct vendor URLs remains. [Older publishing docs](https://smithery.ai/docs/build/publish) still describe a proxied URL flow and vendor verification. Inspect the signed-in publishing UI and establish a surviving direct listing/verification route before submission; do not introduce a managed proxy dependency. |
| Glama / m8/t003, existing w2/088 | [Existing connector](https://glama.ai/mcp/connectors/io.beancount/beancount), OAuth badge; public health is unhealthy, 0.0% over 17 days at the check. | Claim this record, not a duplicate. [FAQ](https://glama.ai/mcp/faq) and connector admin instructions require domain ownership and an authenticated test profile. w2/088 owns the claim, private synthetic QA profile and full day of successful health checks; m8 follows that repair. |
| Docker / m9/t002 | Catalog inclusion unverified; catalog fetch returned 403. | [Official contribution route](https://github.com/docker/mcp-registry): remote Streamable HTTP/OAuth entries are eligible; the [prepared entry](./marketplace-submissions/docker/README.md) passes the pinned upstream validator/catalog generator. Standalone gateway 0.44.1 reaches discovery, DCR and consent; the browser has no dedicated QA session, so no grant/read/preview or submission occurred. Complete the QA journey, then the documented review flow. |
| Cursor / m9/t003 | Official and community inclusion unverified. | [Official marketplace](https://cursor.com/marketplace) and [plugin contribution guide](https://github.com/cursor/community-plugins) have their own publishing process. [cursor.directory](https://cursor.directory/) is a separate community site with its own signed-in submission route. The [MCP-only preparation](./marketplace-submissions/cursor/README.md) passes the official template validator. Both publisher identities sign in; the official final action accepts Publisher Terms, while the community site offers manual or GitHub import. Neither submission was sent; fresh native Cursor QA proof remains under w1/m34/t003. |
| Cline / m9/t004 | Public submission issue search returned no Beancount matches; installed catalog inclusion still unverified. | [Marketplace instructions](https://github.com/cline/mcp-marketplace) require the submission template, a 400×400 PNG and verified README or `llms-install.md` installation. [Prepared icon, setup and issue fields](./marketplace-submissions/cline/README.md) are ready. Required installation/stability confirmations remain unchecked: no actual native Cline QA run or issue submission yet. Remote transport/OAuth support alone does not prove installability. |
| GitHub gallery / m9/t005 | [Gallery search](https://github.com/mcp?search=beancount) returned no MCPs; official registry publication already exists. | Follow [GitHub's registry inclusion process](https://github.blog/ai-and-ml/generative-ai/how-to-find-install-and-manage-mcp-servers-with-the-github-mcp-registry/). The curated gallery has a separate partnership intake; the [operator nomination](./marketplace-submissions/github/README.md) is prepared and unsent. Actual receipt/review remains a separate external gate. |
| VS Code / m9/t005 | Gallery inclusion unverified; direct config exists in the MCP guide. | [VS Code MCP documentation](https://code.visualstudio.com/docs/agent-customization/mcp-servers#find-another-server) describes gallery/discovery and direct configuration. Verify the actual gallery entry and fresh OAuth journey after GitHub inclusion; a JSON config is not a gallery record. |
| Windsurf / m9/t001 | Current [Cascade docs](https://docs.windsurf.com/windsurf/cascade/mcp) redirect to Devin Desktop and state legacy Cascade has no MCP Marketplace/one-click install. | Cascade can use remote config. Do not claim a Cascade marketplace submission route. Revisit if the vendor opens one; Devin Local is a different product and requires a separate eligibility decision. |
| MCPServers.org / m10/t001 | Live [search](https://mcpservers.org/search?query=beancount) shows one unrelated StdioA record and no canonical hosted connector match. | [Submission form](https://mcpservers.org/submit) offers a free $0 route and remote server option, optional registry name and required contact email; stated review within two weeks. Submitted through Free $0 with canonical registry name, endpoint and OAuth; UI confirmed success. [Public-safe receipt and payload](./marketplace-submissions/directories/mcpservers.json). Await moderation and verify the actual public listing/connection; no listing URL is exposed yet. |
| MCPMarket / m10/t002 | [Search](https://mcpmarket.com/search?q=beancount) finds other authors' Beancount projects, not this hosted endpoint. | Live [submit UI](https://mcpmarket.com/submit) distinguishes Remote MCP ($69, no free option shown) from GitHub repository (Free Queue $0; optional $29 priority). Submitted the canonical source repository through the genuine free queue; UI confirmed success, ~4–6 weeks. [Receipt and route correction](./marketplace-submissions/directories/mcpmarket.json). Endpoint/OAuth were not separate free-form fields and must be verified in the actual published record. No payment or paid remote entry was submitted. |
| LobeHub / m10/t003 | [Search](https://lobehub.com/mcp?q=beancount) finds other Beancount projects; no matching bex-co hosted connector confirmed. | [Publisher guide](https://market.lobehub.com/s/publish-mcp) supports a remote `cloudEndpoint`. Requires Node ≥22, interactive login and GitHub connection, plus repository owner/push access. The [prepared remote manifest](./marketplace-submissions/lobehub/README.md) passes field/identifier/endpoint checks; actual CLI preflight reaches the login guard. Interactive sign-in requires explicit Terms/Privacy agreement, awaiting action-time approval; no grant, GitHub connection or submission occurred. Owner/push access and subsequent publication/QA proof remain open. |
| MCP.so / 041 | [Search](https://mcp.so/search?q=beancount) finds other projects, not this hosted endpoint. | [Remote submission form](https://mcp.so/submit) requires a $39 one-time fee at this check. Payment is not approved. Unblock only with explicit fee approval or a documented free route. |
| PulseMCP / 042 | Beancount.io inclusion unverified. Registry publication is not proof of import. | [PulseMCP](https://www.pulsemcp.com/): both new server submissions and edits are paused. Wait for an actual reopen or supported correction route; no submission sent. |

## Reviewer rehearsal

1. Configure the canonical endpoint in the actual directory's supported client.
   Capture UTC date, directory URL, client/version and deployed revision if the
   service exposes it. Record “unavailable” for a revision that is not exposed.
2. An unauthenticated `initialize` must return 401 and a `WWW-Authenticate`
   protected-resource metadata URL. That metadata and the authorization-server
   discovery must return 200. A protected 401 is expected, not an uptime failure.
3. Follow the client's OAuth flow with the dedicated QA account. Check the
   client/redirect identity shown on Beancount.io's consent screen. Use only a
   synthetic QA ledger and the scopes needed for this rehearsal. Keep grants,
   tokens, cookies, contact details and account identifiers outside tracked files.
4. Initialize and enumerate the live tools/resources. Query the dedicated
   synthetic fixture and compare the result with its known expected balance or
   transaction. Fetch identifiers from the service; never paste a production
   ledger's data into a directory or review form.
5. Exercise one write-capable tool that actually supports `dry_run`, using its
   current schema and synthetic inputs. Confirm the preview and read back the
   unchanged ledger. Do not substitute a real write for an unsupported preview.
6. Save a public-safe result: listing URL, transport, client/version, OAuth and
   query outcome, preview outcome, date, revision availability, and any review or
   health gate. Remove private credentials/test-profile configuration from
   screenshots and logs. A pending submission is recorded as pending, not done.

[ADR 019](../../../docs/adrs/ADR019-backend-v2-mcp-host-compatibility.md) requires
host fixtures and real-host evidence before declaring a new host supported.
This packet is preparation; it does not add Smithery, Glama, Cline or LobeHub to
the guide's verified host table. A directory that only links to the direct URL
is verified through the client it actually installs or recommends.
