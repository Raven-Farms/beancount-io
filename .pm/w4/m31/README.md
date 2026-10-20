# w4 · m31 — Bound authentication abuse without losing account recovery

**Worker:** worker1 **Goal:** human and agent callers receive predictable request limits before credential work, while account owners retain a verified recovery path **Status:** todo (t001, t002, t003, t004, t005, t006, t010, t011 done)

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Atomic authentication admission and bounded password verification — **DONE** | 90m | — |
| t002 | Shared mail and OTP budgets with durable asynchronous recovery delivery — **DONE** | 90m | t001 |
| t003 | Expose email-verified sign-in recovery through the shared GraphQL ceremony — **DONE** | 60m | t002 |
| t004 | Add a localized recovery path to the login form — **DONE** | 60m | t003 |
| t010 | Preserve mailbox-verified sign-in when reset mail exhausts shared delivery limits — **DONE** | 45m | t004 |
| t005 | Enforce both user and credential API budgets with bounded outage fallback — **DONE** | 60m | t001, t010 |
| t011 | Keep private authentication links out of copied diagnostic reports — **DONE** | 30m | t005 |
| t006 | Adoption surface — **DONE** | 25m | t004, t005, t010, t011 |
| t007 | Simplify | 30m | t006 |
| t008 | Test coverage | 45m | t006, t007 |
| t009 | Closeout | 15m | t008 |

## Definition of done

- Independent shared IP, email and IP+email budgets precede all first-party password verification; success never resets request-volume quotas, and concurrent attempts cannot bypass the failure budget.
- Unknown accounts perform cost-matched password work; new password/OTP proofs fail closed on Redis unavailability, while existing authenticated sessions have bounded fallback.
- Signup account-existence responses remain explicit. Shared delivery/OTP budgets prevent cross-instance/session bypass, and recovery responses do not wait for account lookup or email providers.
- Account owners can explicitly complete a single-use email ownership challenge and a correct password through the localized login UI; no automatic password-failure email, weakened authorization or new dependencies.
- Authenticated API calls respect both user and credential budgets across eligible surfaces. Refresh, device polling and mail work have independent budgets.
- Backend and dashboard native gates pass, actual Redis concurrency/expiry is exercised, policy and recovery are documented, and all task outcomes are individually shipped. Repository completion does not assert production deployment or measured production impact.

## Source + Goal linkage

- **Source:** user-approved authentication enumeration and rate-limit review and explicit `$pm for w4 and then loopx w4`, 2026-10-19. All evidence and implementation are in this public monorepo.
- **Goal linkage:** **A2 — Frictionless onboarding:** legitimate newcomers can sign in and recover access despite abuse. **A1 — Agent-native accounting:** web, Git and token-based agents share deliberate limits instead of protocol-dependent budgets.
- **Expected outcome:** a newcomer sees actionable retries and can prove mailbox ownership to recover access; automated callers cannot multiply quotas by rotating addresses, sessions or tokens.
- **Why now:** local reproductions found password verification bypassing a serial failure budget under parallel load, unknown-account timing shortcuts and reset responses dependent on provider delivery. The user explicitly accepted signup disclosure while approving this hardening proposal.
- **Adoption surface:** included because this changes first-party login/recovery UX and API retry behavior. New package/skill/catalog entries are unnecessary; existing tables and guidance still require verification.
