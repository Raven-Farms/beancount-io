# w6 · m9 — Reach developer marketplaces and galleries

**Worker:** worker1 **Goal:** Developers discover and connect the hosted MCP server through the supported Docker, Cursor, Cline, and GitHub/VS Code galleries. **Status:** blocked (t001 done; validated/prepared payloads shipped; remaining tasks await QA, operator agreement/contact and platform review)

**Implementation estimate:** ~4½h, excluding external review queues and the standing closing tasks.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Confirm developer-gallery eligibility and existing records — **DONE** | 30m | w6/m8/t001 |
| [t002](./t002.md) | Prepare and submit Docker's remote MCP catalog entry — **BLOCKED** | 60m | t001 |
| [t003](./t003.md) | Package the remote connection for Cursor's official and community marketplaces — **BLOCKED** | 60m | t001 |
| [t004](./t004.md) | Prepare Cline's eligible marketplace submission and remote connection evidence — **BLOCKED** | 45m | t001 |
| [t005](./t005.md) | Prepare GitHub inclusion and verify VS Code's discovery path — **BLOCKED** | 45m | t001 |
| [t006](./t006.md) | Verify publication and fresh discovery across eligible developer galleries | 30m | t002, t003, t004, t005 |
| [t007](./t007.md) | Adoption surface | 30m | t006 |
| [t008](./t008.md) | Simplify | 30m | t007 |
| [t009](./t009.md) | Test coverage | 45m | t007, t008 |
| [t010](./t010.md) | Closeout | 15m | t009 |

## Definition of done

- Docker MCP Catalog, Cursor Marketplace, cursor.directory, Cline Marketplace, and GitHub MCP Registry/VS Code discovery each have a dated eligibility and existing-record decision.
- Every confirmed eligible target has an accepted, public listing and a working discovery-to-OAuth-to-synthetic-query/preview path. A public gallery search is verified separately from generic client compatibility.
- Windsurf/Cascade's current submission route is checked. A source-backed unavailable route is recorded with a revisit condition; an account-access or review wait is blocked work, not an exclusion.
- The distribution uses the current io.beancount/beancount identity and single hosted endpoint, and public payload/evidence lives in the owning backend package.
- Temporary account, operator-contact, deployment, and review gates remain explicit until cleared. No submitted-but-unpublished eligible target is counted as done.

## Source + Goal linkage

- **Source:** Approved brainstorm item 4, materialized at the user's request `$pm 3,4,5,6,7 to w6` on 2026-10-20. The user excluded the previously proposed Claude and ChatGPT milestones. Builds on completed w2/m36 and w6/m7.
- **Goal linkage:** **A3 — Community & distribution** (primary), **A1 — Agent-native accounting** (secondary): distribute the existing accounting connector through supported catalogs and usable install paths.
- **Expected outcome:** Developers find Beancount.io in their existing tool's discovery flow and make a first authenticated MCP call. Signals: gallery installs and successful first queries.
- **Why now:** The shipped registry identity and host implementations make distribution the remaining work. Shared materials depend only on m8/t001, not on Smithery/Glama approval or the separate ClawHub release.
- **Adoption surface:** included because the milestone ships public listings and agent-facing connection instructions. Reuse existing host evidence and canonical setup guidance.

## Execution boundaries

- Reuse `backend-cluster/backend-v2/server.json`, `backend-cluster/backend-v2/docs/mcp.md`, and the shared inventory `backend-cluster/backend-v2/docs/mcp-marketplaces.md`; stage any public submission payload in the owning backend package. Preserve existing REST/GraphQL/MCP parity and documented credential policy.
- Use the hosted endpoint, dedicated QA account, and synthetic ledgers. A gateway/client rehearsal connects to that service; it does not provision another backend stack.
- Search for imported records before submitting. Follow documented marketplace submission routes rather than bulk unsolicited PRs/issues.
- Publisher account access, domain verification, operator contact, and review queues are concrete external gates. Prepare all independent repository work first; park any dependent task through /pm with its exact owner and unblock condition.
- No Claude/ChatGPT publication milestone, ClawHub skills publication, new accounting capability, or paid placement is added here.

## References

- [Docker remote contributions](https://github.com/docker/mcp-registry/blob/main/CONTRIBUTING.md#-adding-a-remote-mcp-server)
- [Cursor plugins](https://prod.cursor.com/docs/plugins)
- [cursor.directory submissions](https://cursor.directory/plugins/new?type=mcp_server)
- [Cline submissions](https://github.com/cline/mcp-marketplace)
- [GitHub inclusion route](https://github.blog/ai-and-ml/generative-ai/how-to-find-install-and-manage-mcp-servers-with-the-github-mcp-registry/)

## Blocked

- **t002:** validated payload, working temporary OCI catalog and standalone discovery/DCR are ready. The dedicated synthetic QA session is established and the consent page selected only that ledger with read/write scopes; no grant/read/preview or submission occurred. **Unblock:** the specific temporary access decision, fresh native OAuth and successful gateway query/preview/unchanged-state/callback, then documented upstream review. **Owner:** QA account holder, repository worker and Docker reviewers in that order. Other gallery preparations proceed independently.

- **t003:** the supported root multi-plugin index validates on the actual repo; official Cursor IDE is installed, and the native Agent completes narrow synthetic OAuth/discovery/query/dry-run with immediate pre/post checks equal. Temporary client cleanup is complete; concurrent QA/file-read limits are recorded in the dated rehearsal. **Unblock:** the remaining IDE conversation under w1/m34/t003, final official Publisher Terms approval, then separate submission/review/publication verification. **Owner:** QA/client account holder, publisher and platform reviewers. IDE absence and nested-repository format are cleared preparation gates.

- **t004:** required icon/setup/issue payload is prepared. Real Cline 4.1.25 setup accepts the URL-only entry; isolated CLI 3.0.73 reaches native OAuth consent, and the dedicated synthetic QA session is available. The exact public catalog feed has no Beancount match across 203 entries/149 MCP servers; the blank native panel is not rendering proof. No grant was approved; required template confirmations stay unchecked. **Unblock:** the specific temporary access decision, fresh OAuth, authenticated discovery/query/preview/unchanged-state, then authorized submission and review. **Owner:** QA/client account holder, repository worker and Cline reviewers.

- **t005:** concrete GitHub nomination is prepared and unsent; actual VS Code `@mcp` opens with 51 entries/50 observed names and no match, without exhaustive/name-filter proof. Install/Copilot OAuth/query/preview remains unverified under w1/m34/t003. **Unblock:** authorized operator request, curated acceptance and fresh native QA discovery/OAuth/query/preview. **Owner:** publisher, GitHub reviewers and QA/client account holder.

- **Milestone / t006–t010:** final publication verification and standing closing acceptance depend on unresolved t002–t005 gates. This does not prevent independent setup, payload validation or documentation substeps inside those tasks. **Unblock:** complete each gate and the actual accepted listing/connection journeys, then finish adoption/simplification/coverage/closeout. **Owners:** recorded account holder/publisher/platforms, then repository worker. Current preparation: Docker fbe47be0e, Cursor 7ed1cfe05, Cline 6e5a556b8 plus the native setup above, GitHub/VS Code bb3f23e4a. No submission or new eligible gallery publication is claimed.
