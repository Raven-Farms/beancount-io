# w6 · m10 — List the connector in independent web directories

**Worker:** worker1 **Goal:** People comparing accounting MCP servers find accurate, usable remote listings on the eligible independent directories. **Status:** todo

**Implementation estimate:** ~2h, excluding external review queues and the standing closing tasks.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Submit or correct MCPServers.org's free remote listing | 30m | w6/m8/t001 |
| [t002](./t002.md) | Submit or correct MCPMarket's free remote listing | 30m | w6/m8/t001 |
| [t003](./t003.md) | Establish LobeHub eligibility and prepare its supported connector listing | 45m | w6/m8/t001 |
| [t004](./t004.md) | Verify the independent-directory listings after moderation | 15m | t001, t002, t003 |
| [t005](./t005.md) | Adoption surface | 30m | t004 |
| [t006](./t006.md) | Simplify | 30m | t005 |
| [t007](./t007.md) | Test coverage | 45m | t005, t006 |
| [t008](./t008.md) | Closeout | 15m | t007 |

## Definition of done

- MCPServers.org and MCPMarket expose one accurate public listing each, submitted through their free routes.
- LobeHub's current eligibility is established from primary requirements. It has a live listing if eligible; a genuine unsupported route is recorded with evidence and a revisit condition.
- Names, repository/source links, official registry identity, endpoint, and OAuth instructions match the deployed connector.
- Every advertised connection path is checked against the hosted synthetic QA setup. Pending moderation, account access, or temporary fetch failures remain open.
- Public listing URLs, dates, and state are recorded in the shared inventory and the public MCP connection guide.

## Source + Goal linkage

- **Source:** Approved brainstorm item 5, materialized at the user's request `$pm 3,4,5,6,7 to w6` on 2026-10-20. The user excluded the previously proposed Claude and ChatGPT milestones. Builds on completed w2/m36 and w6/m7.
- **Goal linkage:** **A3 — Community & distribution** (primary), **A1 — Agent-native accounting** (secondary): distribute the existing accounting connector through supported catalogs and usable install paths.
- **Expected outcome:** People comparing MCP accounting connectors can move from a directory result to working setup instructions. Signals: referral visits and successful first connections.
- **Why now:** The shared packet makes these incremental distribution routes inexpensive. Free moderation queues can start without waiting for other marketplace approval; MCP.so and PulseMCP retain separate gates.
- **Adoption surface:** included because the milestone ships public listings and agent-facing connection instructions. Reuse existing host evidence and canonical setup guidance.

## Execution boundaries

- Reuse `backend-cluster/backend-v2/server.json`, `backend-cluster/backend-v2/docs/mcp.md`, and the shared inventory `backend-cluster/backend-v2/docs/mcp-marketplaces.md`; stage any public submission payload in the owning backend package. Preserve existing REST/GraphQL/MCP parity and documented credential policy.
- Use the hosted endpoint, dedicated QA account, and synthetic ledgers. A gateway/client rehearsal connects to that service; it does not provision another backend stack.
- Search for imported records before submitting. Follow documented marketplace submission routes rather than bulk unsolicited PRs/issues.
- Publisher account access, domain verification, operator contact, and review queues are concrete external gates. Prepare all independent repository work first; park any dependent task through /pm with its exact owner and unblock condition.
- No Claude/ChatGPT publication milestone, ClawHub skills publication, new accounting capability, or paid placement is added here.

## References

- [MCPServers.org submission](https://mcpservers.org/submit)
- [MCPMarket submission](https://mcpmarket.com/submit)
- [LobeHub marketplace eligibility to verify](https://lobehub.com/mcp)
