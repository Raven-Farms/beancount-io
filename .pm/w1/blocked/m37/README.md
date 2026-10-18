# w1 · m37 — Retire the Stripe test tenant and resolve each paid plan from its own subscription

**Worker:** worker1
**Goal:** Remove the built-in `beancount-web-dev` billing tenant and make billing details, effective tier, renewal cache, and resource quotas agree for live subscribers, including accounts with historical test bindings.
**Status:** blocked (t001–t009 shipped and deployed; t011 execution and t010 final closeout remain open)

## Source + Goal linkage

- **Source:** user request on 2026-10-17 to remove the test tenant and fix the billing bugs found during a read-only investigation. A synthetic local reproduction returned PREMIUM for a live Organization price when the cached customer supplied the dev client ID; the same subscription returned ORGANIZATION with the prod client ID. A second reproduction showed `subscriptionStatus()` writing the live renewal date to an unrelated first customer row. Production database row selection has not been verified.
- **Goal linkage:** **A2 — Frictionless onboarding**, with **A1 — Agent-native accounting**: a paid subscriber and their CLI/agent must receive the purchased limits without manual database edits or another purchase.
- **Expected outcome:** settings, account profile, CLI status, and quota enforcement identify the same live plan; legacy test data cannot downgrade or grant access, and refreshing billing cannot change another customer's cache.
- **Why now:** migrating a long-lived test user to live billing exposes two independent ownership bugs. Removing the dev configuration alone would leave the wrong-row assumptions and damaged cache values behind.
- **Adoption surface:** included because checkout/settings behavior and operator billing configuration change. This is a product monorepo: use dashboard feature locale catalogs and language selection, not CMS `i18n/*/code.json` or invented locale routes.

## Scope and constraints

- Retire the application tenant `beancount-web-dev`, its URL switch, runtime credentials, admin selector, deployment plumbing, and developer script defaults. Keep `beancount-web-prod`, recognized legacy live prices, existing billing authorization, and the promotion-code checkout option.
- Stripe's sandbox product is not being removed. Automated verification uses synthetic fixtures/mocks and must never create a charge or redeem a live coupon.
- Resolve plans using each subscription's own client/customer/price tuple. Preserve the existing active-status policy; changing trial, delinquency, refund, or grace-period policy is out of scope.
- Reconcile old application billing bindings with a preview-first, idempotent operation. Do not delete users, ledgers, audit history, or real Stripe customers/subscriptions. Stripe-side cancellations/deletions and credential revocation are outside this milestone.
- All board evidence is public-safe: no customer email, user ID, Stripe account/customer/subscription ID, credentials, or database exports. Keep any real operational report outside tracked files.
- No new credit, complimentary entitlement, or billing platform is needed.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Retire the backend test tenant and its configuration consumers — **DONE** | 40m | — |
| t002 | Resolve tier deterministically from the matching subscription — **DONE** | 35m | t001 |
| t003 | Bind renewal cache writes to the exact subscription customer — **DONE** | 40m | t001 |
| t004 | Reconcile historical test bindings and stale live cache safely — **DONE** | 40m | t002, t003 |
| t005 | Remove the dashboard test billing path and verify plan consistency — **DONE** | 35m | t001, t002, t003 |
| t006 | Remove retired billing copy across every dashboard language — **DONE** | 25m | t005 |
| t011 | Backfill existing users through a bounded verified billing cutover | 40m | t004, t005, t006 |
| t007 | Verify adoption surfaces and document the billing cutover — **DONE** | 25m | t004, t005, t006 |
| t008 | Run `/simplify` over the milestone diff — **DONE** | 25m | t007 |
| t009 | Prove migration, ownership, and quota behavior with meaningful tests — **DONE** | 40m | t007, t008 |
| t010 | Verify the deployed outcome and archive the milestone | 15m | t009, t011 |

**Total estimate:** ~6h; substantive implementation t001–t005 plus t011 totals ~3h50m. t002 and t003 can proceed independently after t001; t004 and t005 can proceed independently once both are complete. t011 owns the actual existing-users rollout using t004's tested tool. Existing IDs are preserved; its row precedes the standing closing work.

## Definition of done

- No supported runtime or dashboard path selects `beancount-web-dev`; stale dev inputs and test events cannot mutate live billing or grant paid limits. Historical test names may remain only in migration/rejection fixtures and explanatory history.
- A synthetic account with an expired test binding and active live Organization subscription resolves to ORGANIZATION regardless of customer row order; dashboard billing and the current-plan/usage panel agree, and the account/profile and quota paths use that same result.
- Renewal refreshes and verified webhooks update only the matching user/client/Stripe-customer binding. Unrelated rows remain byte-for-byte unchanged; repeated/out-of-order refresh cases are covered without inventing subscription policy.
- The retirement/reconciliation procedure has a no-write default, a bounded apply mode, a rollback record outside git, and an idempotence proof. It preserves live subscription state and all account/ledger data.
- Existing users are backfilled across an explicitly inventoried cohort with resumable bounded batches, aggregate completeness counts and verified read-back; unresolved cases remain explicit rather than silently skipped. Tooling without actual execution does not satisfy t011.
- Existing promotion-code checkout support and recognized legacy live plans still work. Retired UI keys are removed from every supported dashboard language; English and Chinese settings are verified through the real language selector.
- Backend typecheck, tests, OpenAPI generation/drift checks and dashboard typecheck, tests, translation checks, and build pass using their normal package scripts. Unrelated failures are recorded with a baseline reproduction, never hidden by changing assertions or test runner semantics.
- Deployment revision and a read-only hosted verification demonstrate settings/profile/CLI and effective quotas agree. No live purchase, coupon redemption, or destructive cleanup is performed as a smoke test. If deployment or authorized data reconciliation is unavailable, keep the corresponding task blocked with its exact unblock condition rather than declaring the milestone done.
- All task statuses and links are consistent; completed tasks and the milestone are moved into `done/` through `/pm`. Planning does not commit or implement this work.

## Implementation evidence — 2026-10-17

- Backend normal full gate: 322 suites / 5,514 tests and one snapshot passed (`NODE_OPTIONS=--max-old-space-size=8192 yarn test --runInBand`; heap capacity only, unchanged compiler/runner semantics). Backend typecheck passes. Real PostgreSQL/CLI integration gate: 5 tests passed with a non-UTC process timezone, including the packaged-script revision safeguard.
- Dashboard normal suite: 519 files / 5,752 tests passed, one existing skip; final settings retest (175 tests) and build also passed. Translation gate: 17 passed. Browser fixture verification used the real English/Chinese language selector and the retired URL flag; both show Organization, 100 ledgers and 50 collaborators.
- Both API generators ran. The public v1 contract is unchanged. Admin generation reflects the prod-only selector and verified-live webhook description, plus pre-existing archive-description drift. Regenerated admin CLI typecheck fails on two already-removed endpoints; regenerating from the original HEAD spec reproduces the same two errors. No unrelated CLI command was removed to hide the baseline issue.
- All four Compose variants validate with their example environments. Production database rows have not been inspected or changed, and no live purchase/promotion was used.
- Dependency correction: adoption docs and local quality gates precede the operational rollout; t010 explicitly depends on both t009 and t011. The actual backfill and deployed read-back remain required by the Definition of done.

## Operational state

Code shipped as `9dfc6275`. Both backend and dashboard deployments completed successfully from that revision through the existing production management UI. Hosted English/Chinese settings (including the retired URL switch) show Organization with the configured 100-ledger / 50-collaborator quota; `bea --json cloud status` returns ORGANIZATION. No live purchase, coupon redemption or subscription mutation was performed. The ordinary fixed settings refresh may update its own verified live period cache; no cohort maintenance backfill has run.

Bex login refresh succeeded, but its separate inventory endpoint returned HTTP 524. The existing production deployment UI was usable and deployment is not blocked by that endpoint. A follow-up connection probe reached the production SSH service using an isolated temporary host-key record, but the server rejected the locally available authentication (`Permission denied`). No application command ran. The only configured Beancount SSH alias is the restricted git service; t011 still needs a working production execution account or terminal.

## Blocked

**t011 and dependent t010 are blocked:** a verified production execution entry (existing SSH alias/known host or authorized deployment terminal) is required. **Unblock:** the operator supplies that entry so the documented preview can inventory the cohort; review its fingerprint, apply bounded batches and record aggregate completeness/idempotence/read-back. No private key or customer report belongs in this board.

## Final local/hosted verification

- Backend typecheck and 5,514 unit tests pass; five PostgreSQL/CLI integration tests pass. Dashboard typecheck, full unit suite, 175-test settings retest, 17 translation checks, full `yarn format:check`, full `yarn lint` (including Knip), and production build pass.
- Staged gitleaks scan and GitHub Secret scan pass. [Backend CI](https://github.com/bex-co/beancount-io/actions/runs/39080597909) completed successfully, including its unit suite and OpenAPI drift gate. [Dashboard CI](https://github.com/bex-co/beancount-io/actions/runs/39080597901) has passed format/lint and is still running tests; no pending job is counted as passed.
- Backend deployment logs explicitly resolved `9dfc62757faff9e8d1ae427d6b13ebed9b983fe2`; dashboard checkout/build used the same revision. Both report SUCCESS. The hosted verification confirms the reported paid-tier mismatch is fixed, but does not replace full cohort execution.
- Completed tasks are under this milestone's `done/`. This milestone remains unchecked and is parked under `blocked/` until the actual backfill and final aggregate read-back hold.
