# w4 · m36 — Preserve profile and commit timestamps through hydration

**Worker:** worker1 **Goal:** Commit, profile activity and repository-card timestamps hydrate without replacing focused controls and show exact browser-zone dates. **Status:** blocked (t001, t002, t004, t005, t007, t008 done; t003 needs the deployed repository-card check)

**Severity:** minor. **Estimate:** 260m across ten tasks, dashboard only.

## Tasks

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Stabilize initial commit relative-time rendering — **DONE** | 45m | — |
| [t002](./done/t002.md) | Synchronize the exact timestamp name after hydration — **DONE** | 25m | t001 |
| [t007](./done/t007.md) | Stabilize profile activity relative text and exact titles — **DONE** | 40m | t001 |
| [t008](./done/t008.md) | Stabilize repository-card relative text and exact titles — **DONE** | 35m | t007 |
| [t003](./t003.md) | Verify the timestamp and keyboard adoption surface | 20m | t002, t007, t008 |
| [t004](./done/t004.md) | Simplify the initial commit/activity lifecycle — **DONE** | 10m | t007 |
| [t005](./done/t005.md) | Prove the initial commit/activity SSR behavior — **DONE** | 40m | t007 |
| [t009](./t009.md) | Simplify the added repository-card lifecycle | 10m | t003 |
| [t010](./t010.md) | Prove repository-card SSR identity and exact titles | 25m | t003 |
| [t006](./t006.md) | Close out and archive the milestone | 10m | t003, t004, t005, t009, t010 |

The completed t004/t005 record the original two-consumer source review and regression work, performed before deployed browser verification was available. Their dependencies now name the last initial implementation, t007. The new t009/t010 cover the added card implementation after the expanded adoption check; completed history does not stand in for that work.

## Definition of done

- [ ] A real server-rendered CommitMetadata hydrated across a relative-age label boundary retains the original timestamp and focused neighboring control, with no React418 recovery.
- [ ] A real public ProfileActivity hydrated across its relative-age boundary retains the existing profile tree and focused Show more ledgers button. Its unchanged activity instants display current relative labels without React418 recovery.
- [ ] A real server-rendered RepositoryListItem crossing a relative-age boundary retains the original card, time nodes and focused sibling control, without React418. Its initial and expanded exact titles match browser time zones, including a UTC/Kiritimati calendar-day difference. Preserve profile collection and Starred rendering.
- [ ] Matching-window controls for all three consumers retain their original nodes/focus; readable SSR timestamps remain available.
- [ ] ProfileActivity's five initial exact-time title attributes and client-expanded rows agree with the browser time zone after hydration, including a UTC/Kiritimati calendar-day difference; their datetime instants stay unchanged.
- [ ] After hydration, the actual time element's accessible name and keyboard tooltip agree with active application language and actual browser time zone, including a UTC/Kiritimati calendar-day difference. The datetime instant never changes.
- [ ] Desktop/narrow, normal client navigation, locale switching, tooltip access and large-diff/file navigation continue working. No API, clock override, new dependency, credential or hosted-content change is needed.
- [ ] Meaningful real SSR/hydration regressions and dashboard format/lint/test/build pass. Record the tested build/target and distinguish local verification from production deployment.
- [ ] Source-only related consumers remain explicitly scoped; do not redesign every relative-time user or add an automatic age ticker.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. See [the live findings](./FINDINGS.md). **A2 — Frictionless onboarding:** a keyboard reader on a slow initial load must retain their place, and exact-time information must describe the browser's local date consistently. Commit, activity and repository-card warnings led to independently controlled startup-delay reproductions at both widths, with matching-window controls. All three relative failures use the same live-clock helper. The independent exact-attribute failures affect CommitMetadata's accessible name and ProfileActivity's native title; only the commit has the separately verified keyboard tooltip. Coordinated initial-render behavior, local consumer integrations, real hydration tests and browser verification exceed one hour. Adoption-surface verification includes public collection discovery as well as commit reading because these controls directly affect onboarding.

## Scope

Repair the three independently proved consumers: CommitMetadata in direct/history CommitDetail layouts; ProfileActivity in ordinary/public profiles; and RepositoryListItem in LedgerCollection and the Starred tab. The collection card is proved live; the second caller is source-audited and must be preserved. Keep localized helpers and exact source instants. Five other relative-time consumers remain audit scope. Do not rewrite every consumer, add an automatic ticker or change API contracts. Physical native title popups, speech and other browser engines remain unverified. QA has made no product changes.

## Deployment verification and remaining work

**Unblocked 2026-10-20** — the previously unavailable deployed SSR build and owned headless browser are now available. Actual held-startup controls at both widths preserve the repaired commit and public activity nodes/focus across real age boundaries. The commit's UTC/Kiritimati DOM, native AX name and keyboard tooltip agree. Public activity titles agree with the browser-zone expression in initial/expanded rows. These controls clear the external access/deploy blocker; t003 remains pending for its full journey and newly added repository-card scope. No whole-milestone completion is claimed.

The initial implementation shipped in c293ab9c1 and the TanStack useHydrated refactor in 21029d403. The prior source worker recorded passing dashboard format/lint/6375 tests/build and real renderToString → hydrateRoot clock/zone regressions for those two consumers. Those historical checks are not claimed to validate the added card implementation.

**Remaining reproduced failure:** unmodified RepositoryListItem still computes clock-dependent text and a runtime-zone title on initial render. At both widths a real startup delay changes its relative phrase, emits React418 and replaces the focused profile tree while other card labels remain stable. A narrow repeat needs only 11.586 seconds (13 → 14 minutes); an immediate-release control retains all nodes/focus. Separately, Kiritimati retains the server-zone title on all 12 initial public cards while 12 newly mounted cards have correct titles. See the appended production controls in [FINDINGS.md](./FINDINGS.md). This extends the same open hydration finding; the finding-group count is unchanged.

## Blocked again

**Blocked 2026-10-20** — t008's repository-card repair shipped; t003's deployed card journey (and t009, t010 and t006 after it) cannot run here.

- **Shipped baseline:** `e38a2b614`. RepositoryListItem reuses the ProfileActivity convention: TanStack `useHydrated`, a UTC exact date as the server/hydration text and title, then the relative age and browser-zone title in place after hydration, with the `datetime` instant unchanged. `repository-list-item-hydration.test.tsx` runs real `renderToString` → `hydrateRoot`: across a 13→14-minute boundary and in a stable window the cards, time nodes and focused sibling button survive with no recoverable error, and under Pacific/Kiritimati the initial and newly rendered card titles match the browser expression (Jul 28 versus the server's Jul 27). It fails with the change reverted. Test mocks for LedgerCollection, profile tabs and date-locale gained `useHydrated`/`i18n`; dashboard format, lint, test and build pass. The task table's duplicated rows were removed.
- **Blocker:** t003's added repository-card acceptance needs the deployed build and a held-startup browser at 1440 and 390; this worker has neither.
- **Unblock:** after `e38a2b614` or later is deployed, QA repeats FINDINGS.md's held-startup card boundary and the UTC/Kiritimati 12-card title comparison at both widths, confirming focus and nodes survive without React418 and initial/expanded titles agree; then close t003, run t009's /simplify, complete t010 (the hydration test above is its starting point) and t006. **Who:** the user (deploy) and the dashboard QA loop.

