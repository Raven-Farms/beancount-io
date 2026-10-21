# w4 · m39 — Recover Journal and dashboard from malformed saved lists

**Worker:** worker1 **Goal:** Invalid optional browser preferences cannot trap the Journal or signed-in dashboard behind an error screen. **Status:** blocked (t001, t002 done; t003 and t005 need fresh 1440/390 browser checks)

**Severity:** minor. **Estimate:** 135m across six tasks, dashboard only.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Validate persisted Journal filter arrays — **DONE** | 45m | — |
| [t002](./done/t002.md) | Validate changelog read identities on mount and sync — **DONE** | 35m | t001 |
| [t003](./t003.md) | Verify preference recovery across adoption surfaces | 10m | t002 |
| [t004](./t004.md) | Simplify the bounded preference decoding | 10m | t003 |
| [t005](./t005.md) | Prove recovery and preserve valid saved choices | 30m | t003 |
| [t006](./t006.md) | Close out and archive the milestone | 5m | t004, t005 |

## Definition of done

- [ ] Valid-JSON wrong-shaped saved Journal arrays and changelog readIds cannot crash either page; reload works without manual browser-storage cleanup.
- [ ] Journal defaults recover from invalid containers, supported directive values and valid subtype strings remain intact, and invalid values never reach GraphQL variables. Preserve valid empty arrays and ledger-scoped keys.
- [ ] Changelog native cross-tab updates cannot publish an invalid iterable into render. Preserve valid release identities, unread semantics, valid timestamp watermarks and last known good state on invalid incoming updates.
- [ ] Ordinary valid preferences, unrelated storage keys, Journal Metadata/Postings choices, pagination/filter behavior and device-local changelog policy remain unchanged. No global storage reset, server persistence or new dependency.
- [ ] Meaningful component/transport/native-storage-event regressions and dashboard format/lint/test/build pass. Record tested build, cleanup and deployment limits before closeout.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. [Live findings](./FINDINGS.md) reproduce both failures in the running client with controlled malformed local preferences. **A2 — Frictionless onboarding:** an optional local display/read preference must not make financial records or the home page unusable until a user discovers developer tools. Journal's inline Retry and the dashboard's root Retry/reload retain the invalid cache and fail again. Two distinct preference consumers, cross-tab behavior and regression controls exceed one hour. This milestone ships customer-facing recovery, so adoption verification is included.

## Scope

Journal's four persisted filter-array keys and the changelog readIds list, using the existing useLocalStorageState deserializer boundary. Reuse a small decoder where appropriate, without replacing the storage system or inferring arbitrary generic types at runtime. Completed [W4/272](../done/272.md) owns the BQL history consumer independently; preserve its decoder and coordinate any shared validation without duplicating its implementation task or importing that feature's history policy. Overview's separate layout normalizer already checks its saved structure and is outside this repair. No API/backend, authentication, ledger write or persistent server preference change is required.

## Blocked

**Blocked 2026-10-20** — the code and its regressions shipped; the browser checks t003 and t005 require (and therefore t004 Simplify and t006 Closeout, which follow t003) cannot run here.

- **Shipped baseline:** `536a2619a` decodes Journal's four saved filter lists through the new shared `common/lib/storage/decode-string-list.ts` (a non-list throws, so `useLocalStorageState` uses the default on load and keeps the last good value on a cross-tab update; non-string or unknown directive members are dropped before render and GraphQL variables). `9d53761d1` decodes changelog `readIds` the same way. `48d13ad09` adds the real WhatsNew-over-real-hook composition test. `journal-saved-filters.test.tsx` (actual query variables for object/null/scalar/mixed/empty lists), `use-changelog-watermark.test.tsx` (initial and native `StorageEvent` cases) and `whats-new-saved-reads.test.tsx` fail with the guards reverted. Dashboard format, lint, test and build pass. W4/272's BQL history decoder is untouched; the dashboard AGENTS.md What's new section needed no change.
- **Blocker:** t003/t005 require fresh desktop (1440) and narrow (390) browser runs of the public Journal and the signed-in dashboard with controlled malformed storage, reload and a real second-tab update; no browser is available to this worker.
- **Unblock:** after `48d13ad09` or later is deployed, QA repeats FINDINGS.md's Journal and dashboard reproductions at 1440 and 390, confirms both pages render without manual storage cleanup, that reload and a second-tab write of a wrong-shaped readIds keep the dashboard usable, and that valid saved filters and read state survive; then close t003/t005, run t004's /simplify and t006. **Who:** the user (deploy) and the dashboard QA loop.

