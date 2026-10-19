# w0 · m8 — Ledger archive downloads stream straight from Gitea

**Worker:** worker1 **Goal:** a ledger archive download never holds the whole archive in a service's memory: backend-v2 streams the Gitea archive straight to the caller, the ledger service's buffering hop is gone, and the MCP archive blob (which must be held in memory) has a size cap that points to the streaming URL **Status:** todo (t001–t006 done)

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | backend-v2 streams the archive from Gitea directly | 45m | — | — **DONE**
| t002 | Retire the ledger service's archive route | 30m | t001 | — **DONE**
| t003 | Cap the MCP `ledgerArchive` blob and point past it to the download URL | 30m | t001 | — **DONE**
| t004 | Adoption surface | 15m | t002, t003 | — **DONE**
| t005 | Simplify | 15m | t004 | — **DONE**
| t006 | Test coverage | 30m | t004, t005 | — **DONE**
| t007 | Closeout | 10m | t006 |

## Definition of done

- `GET /api-gateway/v1/ledgers/{owner}/{name}/archive/{archive}` and the deprecated `GET /api-gateway/ledgers/{ledgerId}/archive/{archive}` return the same bytes, `Content-Type` and `Content-Disposition` as before, read from Gitea by backend-v2 with no intermediate buffer. In the local stack, downloading an archive of at least 200 MB raises backend-v2's resident memory by a small, size-independent amount (numbers recorded in the closeout).
- A caller that disconnects mid-download aborts the upstream Gitea request, and an upstream that sends no response headers within the deadline fails with the existing "Ledger archive" unavailable error.
- The ledger service has no archive route. `backend-cluster/idl/beancount-ledger.openapi.json` and the generated ledger clients no longer list it, and no caller depends on it.
- MCP `beancount://{owner}/{name}/archive/{archive}` returns archives at or under the cap as today. Above it, the read is refused without reading more than the cap, and the error's hint names `beancount://{owner}/{name}/archive-download-url`.
- Authorization, the anonymous public-ledger read, and the shared archive-download rate budget behave exactly as before. `surface-parity.test.ts` keeps `gql: 0`, `rest: 0`, `mcp: 0`, and backend-v2 and ledger gates pass.

## Source + Goal linkage

- **Source:** security review of `main` (2026-10-18) and the owner's decision the same day to keep the feature and forward Gitea directly rather than remove it. Today the path is backend-v2 `LedgerArchiveService.download` (`backend-cluster/backend-v2/src/features/ledger/service/ledger-archive-service.ts`) → ledger service `GET /ledgers/:owner/:repo_name/archive/:archive` (`backend-cluster/ledger/src/api/files.ts:312-347`) → Gitea. backend-v2 already streams its half (`api/rest/archive-proxy.ts`, `ctx.body = response.body`), but the ledger hop does `Buffer.from(await upstream.arrayBuffer())` (`files.ts:345`) with no timeout and no size cap. It adds nothing else: it forwards the `Authorization` header backend-v2 built. The MCP resource buffers and base64-encodes on its own (`features/ai-agent/api/mcp-resources.ts:114`). backend-v2 already proxies Git traffic straight to `config.gitea.internalBaseUrl` (`features/gitea/api/git-proxy-handler.ts`).
- **Goal linkage:** **A3 — Community & distribution.** "Download ZIP" is the one-click way to take your plain-text ledger with you, a credibility point for a hosted ledger, and it should not be able to take the shared ledger service down. MCP clients (A1) keep their archive read.
- **Expected outcome:** anyone can download their ledger archive, through the dashboard, REST or an agent's download URL, at any size Gitea serves, without that download costing memory proportional to its size in either service.
- **Why now:** this is the remaining confirmed availability finding from that review after [m5](../done/m5/README.md). The fix is small because both halves (backend-v2 streaming, direct Gitea access) already exist.
- **Adoption surface:** included. The MCP `ledgerArchive` resource description gains the cap and its alternative.
- **Not in scope, by the owner's decision (2026-10-18):** a repository size limit. `assertRepoSizeWithinLimit` (`backend-cluster/ledger/src/features/ledger/operations/assert-repo-size-within-limit.ts`) is unwired today, and it stays untouched here.
