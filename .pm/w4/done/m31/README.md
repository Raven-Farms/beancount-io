# w4 · m31 — Bound authentication abuse without losing account recovery

**Worker:** worker1 **Goal:** human and agent callers receive predictable request limits before credential work, while account owners retain a verified recovery path **Status:** done

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
| t007 | Simplify — **DONE** | 30m | t006 |
| t008 | Test coverage — **DONE** | 45m | t006, t007 |
| t009 | Closeout — **DONE** | 15m | t008 |

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

## Shipped outcomes and final verification

| Item | Shipped revision | Result |
| --- | --- | --- |
| t001 | `2e69bebb5` | Front-loaded IP/email/pair admission, atomic failure reservations, cost-matched dummy work, bounded comparisons and locked session issuance |
| t002 | `abdeb8374` | Shared mail/OTP policies, durable encrypted outbox and one-use proofs |
| t003 | `baafc2b6f` | Real first-party GraphQL request/verification/session ceremony with explicit protocol policy |
| t004 | `a72d02570` | Localized accessible recovery UI, explicit sending and safe continuation |
| t010 | `3f30a8bd6` | Already delivered reset mail can prove mailbox ownership within the original proof lifetime; stable independent reset expiry |
| t005 | `df5195364` | Independent user/credential canonical quotas and bounded existing-session outage fallback |
| t011 | `ed194ff36` | Private auth proof sanitization in copied reports and recovery route metadata |
| t006 | `4855a51bc` | Source-audited operator policy, recovery journey, prerequisites, privacy and tuning guide |
| t007 | `e9e2d5af5` | Behavior-preserving review and removal of retired counter interfaces |
| t008 | `e690948c0` | Real mixed-adapter quota regression plus fresh behavioral RED/GREEN evidence |
| t009 | This closeout commit — **DONE** | Acceptance, shipment and board-state audit; no runtime change |

The t010 implementation is in `3f30a8bd6`; the earlier `96d3a3eb1` recorded completion before its tracked implementation was included. That staging mistake was corrected immediately in the public follow-up. No rewritten remote history is required.

Final backend checks: Node 22, **365 suites / 6246 tests / one snapshot passed**, typecheck, lint/Knip and OpenAPI regeneration without drift. Actual isolated Redis admission/infrastructure verification: six suites / 52 tests; issued-token integration: six additional tests. Historical pre-fix API policy admits update 31 in the new adapter test; labeled unsafe parallel/dummy-work mutations also fail their behavior assertions. Assertions and saved logs are described in t008, and disposable helper code was removed.

Final dashboard checks at `ed194ff36`: **579 files / 6298 passed / one existing skip**, format, lint/typecheck/Knip/i18n and build passed. The dashboard tree has not changed since those gates; backend-only later changes do not invalidate that result. The guidance checker passes all 17 scopes; root package tables, quickstarts, instruction links and the recovery entry were checked. The owning guide links resolve. No new dependency, package or skill was added.

Signup's account-existence disclosure remains the accepted product behavior. New password/OTP/proof admission refuses unavailable security state. Existing API local shadows remain per process and do not promise cross-instance coordination during a Redis partition. Already delivered proof recovery is bounded by the unchanged ten-minute proof lifetime and delivery quotas.

Verification uses real adapters/services, controlled SQL/provider dependencies, actual Lua on isolated Redis and real React/Apollo in JSDOM/SSR. It does not claim live PostgreSQL crash recovery, actual provider delivery, device E2E, production deployment, measured abuse reduction or statistically identical end-to-end account timing. Full-directory secret scans continue to find pre-existing ignored runtime/dependency artifacts; exact staged exports are clean.

Independent follow-up [w4/231](../231.md) records stale agent-facing MCP handshake-budget wording discovered during verification. It is now resolved in its own shipped outcome; that wording fix does not alter the enforced policy verified here.
