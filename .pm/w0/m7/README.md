# w0 · m7 — Login limits key on a trusted client address and on the account

**Worker:** worker1 **Goal:** every rate limiter reads the client address from one helper that trusts only the deployment's own proxy hop, and repeated wrong passwords for one account are limited across addresses and across dashboard and Git sign-in **Status:** todo (t001 done)

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | One trusted client-address helper for REST, GraphQL and Git | 40m | — | — **DONE**
| t002 | Per-account failed-password budget shared by `signIn` and Git basic auth | 60m | t001 |
| t003 | Adoption surface | 20m | t002 |
| t004 | Simplify | 15m | t003 |
| t005 | Test coverage | 30m | t003, t004 |
| t006 | Closeout | 10m | t005 |

## Definition of done

- Changing an inbound `X-Forwarded-For` value does not change the rate-limit bucket of a request on REST, GraphQL or the Git proxy when the server sits behind the configured number of trusted proxies; with no trusted proxy configured, the socket address is used.
- After N wrong passwords for one account within the window, further password attempts for that account are refused on both `Mutation.signIn` and Git HTTP basic auth regardless of client address, with the same generic message for known and unknown accounts. Existing sessions and SSH-key Git access are unaffected, and a successful password reset clears the counter.
- The Git proxy's failed-auth limiter uses the shared Redis counter, not process memory.
- Backend-v2 typecheck, lint and tests pass, and the deploy docs say how to set the trusted-proxy count for each shipped target.

## Source + Goal linkage

- **Source:** security review of `main` (2026-10-18). The GraphQL limiter takes the left-most `X-Forwarded-For` entry directly (`backend-cluster/backend-v2/src/server/graphql/rate-limit-middleware.ts:24-27`), and REST uses `ctx.ip` with Koa's `proxy` always on and no hop count (`config.ts:453`, `server/start-server.ts:59`). Both comments say the left-most entry is client-controlled. The shipped Caddy configs replace an untrusted client's header, so this is not exploitable behind them, but the app does not require or verify that. Separately, `AuthService.loginUser` (`features/auth/service/auth-service.ts:242-269`) has no per-account failure count, and the Git proxy's failed-auth limiter (`features/gitea/api/git-proxy-handler.ts:520-556`) is in-memory, per address, and runs only after a wrong password.
- **Goal linkage:** **A3 — Community & distribution.** Self-hosters run the bundled stack behind proxies of their own; the limiter has to be right for their ingress too, and account protection should not depend on the client address at all.
- **Expected outcome:** password guessing against one account is bounded no matter how many addresses it comes from, and a self-hoster can tell the backend how many proxies to trust.
- **Why now:** these are the remaining gaps from that review's rate-limit finding; both are contained in backend-v2.
- **Adoption surface:** included. Login and Git sign-in gain a refusal message, and the deploy docs gain a setting.
