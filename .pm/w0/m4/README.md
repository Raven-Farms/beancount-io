# w0 · m4 — A password reset ends every session the old password issued

**Worker:** worker1 **Goal:** completing a password reset signs out every existing browser and CLI session and revokes every OAuth grant (mobile refresh tokens included), so a reset actually evicts someone who held the old credentials **Status:** todo

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | Reset revokes every session JWT in the same transaction as the password change | 30m | — |
| t002 | Reset revokes every OAuth grant, refresh token and provider session the user holds | 60m | t001 |
| t003 | Adoption surface | 20m | t002 |
| t004 | Simplify | 15m | t003 |
| t005 | Test coverage | 30m | t003, t004 |
| t006 | Closeout | 10m | t005 |

## Definition of done

- After `Mutation.resetPassword` succeeds, every session JWT issued before it fails verification (`jwts` rows for the user are gone), including a session the same browser held.
- After the reset, every OAuth access token, refresh token and grant for the user is rejected, and the mobile app's next refresh sends it to sign-in instead of an error loop.
- A failed password update leaves the sessions and grants intact and the reset token consumed, as today.
- Backend-v2 typecheck, lint and tests pass. `Mutation.resetPassword` is `gqlOnly` (`op-class.ts`), so there is no REST or MCP adapter to keep in parity.

## Source + Goal linkage

- **Source:** security review of `main` (2026-10-18). `AuthService.resetPassword` (`backend-cluster/backend-v2/src/features/auth/service/auth-service.ts:381-414`) consumes the reset token and calls `user.updatePassword`, but never calls `jwt.deleteByUserId` (`features/auth/data/jwt-model/postgres-impl.ts:115`), which only account deletion uses (`account-service.ts:385`). Session verification requires a `jwts` row (`postgres-impl.ts:94-102`), the default session lifetime is 525600 minutes (`config.ts:392`), and `refreshToken` lets a session renew itself. OAuth refresh tokens and grants also survive. Reset is the only password-update path, so today a user has no way to sign out other devices short of deleting the account.
- **Goal linkage:** **A3 — Community & distribution.** A hosted service holding people's financial ledgers is only credible if account recovery recovers the account.
- **Expected outcome:** a user who resets their password knows every other device, CLI login and connected OAuth client has been signed out.
- **Why now:** this is the most consequential open item from that review. The revocation primitive for sessions already exists, so the sessions half is small.
- **Adoption surface:** included. The reset now signs users out elsewhere, which the reset success copy and the auth docs should say.
