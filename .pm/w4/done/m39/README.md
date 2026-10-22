# w4 · m39 — Recover Journal and dashboard from malformed saved lists

**Worker:** worker1 **Goal:** Invalid optional browser preferences cannot trap the Journal or signed-in dashboard behind an error screen. **Status:** done

**Severity:** minor. **Estimate:** 160m across seven tasks, dashboard only.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Validate persisted Journal filter arrays — **DONE** | 45m | — |
| [t002](./done/t002.md) | Validate changelog read identities on mount and sync — **DONE** | 35m | t001 |
| [t007](./done/t007.md) | Validate saved subtype strings against supported Journal kinds — **DONE** | 25m | t001 |
| [t003](./done/t003.md) | Verify preference recovery across adoption surfaces — **DONE** | 10m | t002, t007 |
| [t004](./done/t004.md) | Simplify the bounded preference decoding — **DONE** | 10m | t003 |
| [t005](./done/t005.md) | Prove recovery and preserve valid saved choices — **DONE** | 30m | t003 |
| [t006](./done/t006.md) | Close out and archive the milestone — **DONE** | 5m | t004, t005 |

## Definition of done

- [x] Valid-JSON wrong-shaped saved Journal arrays and changelog readIds cannot crash either page; reload works without manual browser-storage cleanup.
- [x] Journal defaults recover from invalid containers, supported directive and subtype values remain intact, and invalid values never reach GraphQL variables. Preserve valid empty arrays and ledger-scoped keys.
- [x] Changelog native cross-tab updates cannot publish an invalid iterable into render. Preserve valid release identities, unread semantics, valid timestamp watermarks and last known good state on invalid incoming updates.
- [x] Ordinary valid preferences, unrelated storage keys, Journal Metadata/Postings choices, pagination/filter behavior and device-local changelog policy remain unchanged. No global storage reset, server persistence or new dependency.
- [x] Meaningful component/transport/native-storage-event regressions and dashboard format/lint/test/build pass. Record tested build, cleanup and deployment limits before closeout.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. [Live findings](./FINDINGS.md) reproduce both failures in the running client with controlled malformed local preferences. **A2 — Frictionless onboarding:** an optional local display/read preference must not make financial records or the home page unusable until a user discovers developer tools. Journal's inline Retry and the dashboard's root Retry/reload retain the invalid cache and fail again. Two distinct preference consumers, cross-tab behavior and regression controls exceed one hour. This milestone ships customer-facing recovery, so adoption verification is included.

## Scope

Journal's four persisted filter-array keys and the changelog readIds list, using the existing useLocalStorageState deserializer boundary. Reuse a small decoder where appropriate, without replacing the storage system or inferring arbitrary generic types at runtime. Completed [W4/272](../272.md) owns the BQL history consumer independently; preserve its decoder and coordinate any shared validation without duplicating its implementation task or importing that feature's history policy. Overview's separate layout normalizer already checks its saved structure and is outside this repair. No API/backend, authentication, ledger write or persistent server preference change is required.

## Deployment verification and remaining work

**Unblocked 2026-10-22** — the repaired sources are deployed, and fresh1440/390 browser controls pass the original malformed-container Journal and dashboard crashes, reload, valid preferences and genuine second-tab updates. The browser/deployment blocker is cleared. The same pass found a narrower domain-validation residual: unsupported subtype strings still reach GraphQL and persistently hide Journal behind BAD_USER_INPUT. New t007 owns that bounded dashboard follow-up; t003–t006 remain open. Evidence and the previous blocker are retained in [FINDINGS.md](./FINDINGS.md).

## Closeout (2026-10-22)

- **Implementation:**
  - `536a2619a` and `9d53761d1` decode saved Journal filter lists and changelog read identities at their storage boundaries.
  - t007 restricts each saved subtype list to the values its filter buttons offer (`journal-filter-buttons.ts`), so an unsupported saved kind can no longer make the journal API refuse every read. Valid values, empty selections, per-ledger keys and unrelated preferences are unchanged.
  - No global storage reset, server persistence, backend change or dependency.
- **Evidence:**
  - QA's deployed checks on 2026-10-22 cover the original malformed containers, the dashboard and cross-tab sync ([FINDINGS.md](./FINDINGS.md)).
  - A local production build at 1440 and 390 px loads QA's three unsupported saved subtypes with a 60-row Journal, and sends the supported ones unchanged.
  - The regressions fail with the guards removed ([t005](./done/t005.md)).
- **Gates:** dashboard `yarn format:check`, `yarn lint`, `yarn test` (641 files, 6703 tests) and `yarn build` pass.
- **Limits:**
  - The t007 change is verified locally; QA's post-deploy repeat is still owed.
  - Saved browser values are filtered when read, not rewritten.
  - Physical devices and other engines are unverified.
