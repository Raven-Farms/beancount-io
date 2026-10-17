# w6 · m7 — Connect OpenClaw and Hermes Agent to the hosted MCP endpoint

**Worker:** worker1 **Goal:** OpenClaw and Hermes Agent become named hosts in the sense of ADR 019 D8. Each has a fixture that registers the way the host really does, a dated real sign-in against `https://beancount.io/api-gateway/mcp`, and a per-host row in `docs/mcp.md` that tells its users exactly how to connect. **Status:** todo

**Research date:** 2026-10-16. Sources: OpenClaw's `tools/mcp` and MCP transport pages at `docs.openclaw.ai`; Hermes Agent's MCP page at `hermes-agent.nousresearch.com/docs/user-guide/features/mcp`. t001 confirms every host behavior below first-hand before any fixture relies on it.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Capture how OpenClaw and Hermes Agent identify themselves and redirect | 45m | — |
| t002 | Add OpenClaw and Hermes fixtures to the OAuth host tests | 45m | t001 |
| t003 | OpenClaw: real sign-in, one read, one `dry_run` write | 45m | t001 |
| t004 | Hermes Agent: real sign-in, one read, one `dry_run` write | 45m | t001 |
| t005 | Add both hosts to the per-host notes and ADR 019 | 30m | t002, t003, t004 |
| t006 | Adoption surface | 30m | t005 |
| t007 | Simplify | 30m | t006 |
| t008 | Test coverage | 45m | t006, t007 |
| t009 | Closeout | 15m | t008 |

## What the hosts do (as documented, 2026-10-16)

- **Neither host has an MCP directory we can submit to.** OpenClaw adds servers by hand (Settings, the composer, `openclaw mcp add`, or config). Hermes's `hermes mcp catalog` lists only Nous-approved entries kept in its own repository. So on these hosts, being listed means a verified connection path documented where their users look.
- **OpenClaw:** `openclaw mcp add <name> --url <url> --transport streamable-http`, with `auth: "oauth"`, then `openclaw mcp login <name>` (a `--code` form exists for when the browser cannot reach the callback), then `openclaw mcp doctor <name> --probe`. CLI sign-in captures a loopback redirect. OpenClaw's docs also describe per-requester OAuth (`oauth.identity: "per-requester"`) on a gateway with a public HTTPS origin. In that mode each sender signs in separately, and the redirect is a web URI on the gateway's own origin. On `insufficient_scope` it asks for a fresh login rather than retrying a refresh. Its docs focus on tools, and they do not confirm that it consumes resources or prompts.
- **Hermes Agent:** `mcp_servers.<name>` in `~/.hermes/config.yaml` with `url` and `auth: oauth`, or the `hermes mcp` commands. Hermes identifies itself by a client ID metadata document (CIMD) when the server supports one and falls back to dynamic registration otherwise. It uses PKCE, opens a browser, and waits for a loopback callback. Tokens are cached in `~/.hermes/mcp-tokens/<server>.json`. It exposes resources and prompts to the model as wrapper tools (`list_resources`, `read_resource`, `list_prompts`, `get_prompt`). Its headless option `hermes mcp login <server> --flow device` needs an OAuth device-authorization grant, which `oidc-route.ts` does not enable today.
- **Our side:** discovery, CIMD, DCR that defaults to `native` when `application_type` is absent, and the consent page that names the requester all shipped in w1/m30–m33 and are deployed. `docs/mcp.md` § Per-host notes calls a host supported only if it has a fixture in `oidc-route.test.ts`.

## Definition of done

- `oidc-route.test.ts` has a fixture for OpenClaw's CLI sign-in and for Hermes Agent's. Each registers, or presents its CIMD document, exactly as t001 recorded, then authorizes with the redirect that host really uses. Both pass. If OpenClaw's per-requester gateway mode differs, it has its own fixture or a documented reason why not.
- Each host completed a real sign-in with the dedicated QA account, one read, and one `dry_run` write on the hosted endpoint. Each run is recorded with its date, host version, and the deployed backend revision.
- `docs/mcp.md` has an OpenClaw row and a Hermes Agent row. Each row gives the exact add-and-login commands and states how the host identifies itself, which redirect it uses, and what it consumes (tools only, or resources and prompts through wrapper tools). Hermes's device-code flow is marked unsupported, with the paste-back or port-forward alternative.
- ADR 019 records both hosts in an amendment. Every gap found is either fixed with a test or filed as a `w6` inbox note.

## Source + Goal linkage

- **Source:** user request 2026-10-16 to list Beancount.io on OpenClaw and Hermes Agent. [ADR 019](../../../docs/adrs/ADR019-backend-v2-mcp-host-compatibility.md) D1 (one endpoint for every host) and D8 (every named host has a fixture). Research the same day into both hosts' MCP documentation.
- **Goal linkage:** **A1 — Agent-native accounting.** Two widely used open-source agents can read and write a hosted ledger through the same endpoint that Claude, ChatGPT, Cursor, and Copilot use. Secondary **A3 — Community & distribution**: a documented, verified connection is the listing these hosts offer, and it is the evidence a future Hermes catalog entry would need.
- **Expected outcome:** an OpenClaw or Hermes user pastes two documented commands, approves Beancount.io's consent page, and the agent works on their ledger. Signals: MCP sessions per host on the hosted endpoint.
- **Why now:** the authorization work these hosts depend on is on production (w1/m30–m33, deployed 2026-10-08), and both hosts already speak CIMD or DCR with PKCE, so the remaining work is evidence and docs, not new protocol. Unlike [w1/m34](../../w1/blocked/m34/README.md), whose hosts need the user's own accounts on hosted services, both hosts here run locally from open source. Only the QA account and, for an agent turn, a model provider key are needed. Per [DO_NOT_DO](../../DO_NOT_DO.md), real-client runs use the hosted endpoint, the QA account, and synthetic ledgers, never a second stack. Adoption surface is included because the milestone changes the public MCP connection docs.

## Out of scope

- A pull request to Hermes's `optional-mcps/` catalog. Nous curates it, and the docs describe no community submissions. Revisit only if Nous invites one.
- OAuth device-authorization grant on the authorization server. If t004 shows headless Hermes users need it, file it as its own milestone with the REST/GraphQL/MCP parity check.
- Skills on ClawHub ([w6/m6](../blocked/m6/README.md)). Host-specific MCP endpoints, tools, or code (ADR 019 D1).
