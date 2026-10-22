# w4 · m36 — Preserve profile and commit timestamps through hydration

**Worker:** worker1 **Goal:** Commit, profile activity and repository-card timestamps hydrate without replacing focused controls and show exact browser-zone dates. **Status:** done

**Severity:** minor. **Estimate:** 260m across ten tasks, dashboard only.

## Tasks

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Stabilize initial commit relative-time rendering — **DONE** | 45m | — |
| [t002](./done/t002.md) | Synchronize the exact timestamp name after hydration — **DONE** | 25m | t001 |
| [t007](./done/t007.md) | Stabilize profile activity relative text and exact titles — **DONE** | 40m | t001 |
| [t008](./done/t008.md) | Stabilize repository-card relative text and exact titles — **DONE** | 35m | t007 |
| [t003](./done/t003.md) | Verify the timestamp and keyboard adoption surface — **DONE** | 20m | t002, t007, t008 |
| [t004](./done/t004.md) | Simplify the initial commit/activity lifecycle — **DONE** | 10m | t007 |
| [t005](./done/t005.md) | Prove the initial commit/activity SSR behavior — **DONE** | 40m | t007 |
| [t009](./done/t009.md) | Simplify the added repository-card lifecycle — **DONE** | 10m | t003 |
| [t010](./done/t010.md) | Prove repository-card SSR identity and exact titles — **DONE** | 25m | t003 |
| [t006](./done/t006.md) | Close out and archive the milestone — **DONE** | 10m | t003, t004, t005, t009, t010 |

The completed t004/t005 record the original two-consumer source review and regression work, performed before deployed browser verification was available. Their dependencies now name the last initial implementation, t007. The new t009/t010 cover the added card implementation after the expanded adoption check; completed history does not stand in for that work.

## Definition of done

- [x] A real server-rendered CommitMetadata hydrated across a relative-age label boundary retains the original timestamp and focused neighboring control, with no React418 recovery.
- [x] A real public ProfileActivity hydrated across its relative-age boundary retains the existing profile tree and focused Show more ledgers button. Its unchanged activity instants display current relative labels without React418 recovery.
- [x] A real server-rendered RepositoryListItem crossing a relative-age boundary retains the original card, time nodes and focused sibling control, without React418. Its initial and expanded exact titles match browser time zones, including a UTC/Kiritimati calendar-day difference. Preserve profile collection and Starred rendering.
- [x] Matching-window controls for all three consumers retain their original nodes/focus; readable SSR timestamps remain available.
- [x] ProfileActivity's five initial exact-time title attributes and client-expanded rows agree with the browser time zone after hydration, including a UTC/Kiritimati calendar-day difference; their datetime instants stay unchanged.
- [x] After hydration, the actual time element's accessible name and keyboard tooltip agree with active application language and actual browser time zone, including a UTC/Kiritimati calendar-day difference. The datetime instant never changes.
- [x] Desktop/narrow, normal client navigation, locale switching, tooltip access and large-diff/file navigation continue working. No API, clock override, new dependency, credential or hosted-content change is needed.
- [x] Meaningful real SSR/hydration regressions and dashboard format/lint/test/build pass. Record the tested build/target and distinguish local verification from production deployment.
- [x] Source-only related consumers remain explicitly scoped; do not redesign every relative-time user or add an automatic age ticker.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. See [the live findings](./FINDINGS.md). **A2 — Frictionless onboarding:** a keyboard reader on a slow initial load must retain their place, and exact-time information must describe the browser's local date consistently. Commit, activity and repository-card warnings led to independently controlled startup-delay reproductions at both widths, with matching-window controls. All three relative failures use the same live-clock helper. The independent exact-attribute failures affect CommitMetadata's accessible name and ProfileActivity's native title; only the commit has the separately verified keyboard tooltip. Coordinated initial-render behavior, local consumer integrations, real hydration tests and browser verification exceed one hour. Adoption-surface verification includes public collection discovery as well as commit reading because these controls directly affect onboarding.

## Scope

Repair the three independently proved consumers: CommitMetadata in direct/history CommitDetail layouts; ProfileActivity in ordinary/public profiles; and RepositoryListItem in LedgerCollection and the Starred tab. The collection card is proved live; the second caller is source-audited and must be preserved. Keep localized helpers and exact source instants. Five other relative-time consumers remain audit scope. Do not rewrite every consumer, add an automatic ticker or change API contracts. Physical native title popups, speech and other browser engines remain unverified. QA has made no product changes.

## Deployment verification and remaining work

**Unblocked 2026-10-20** — the previously unavailable deployed SSR build and owned headless browser are now available. Actual held-startup controls at both widths preserve the repaired commit and public activity nodes/focus across real age boundaries. The commit's UTC/Kiritimati DOM, native AX name and keyboard tooltip agree. Public activity titles agree with the browser-zone expression in initial/expanded rows. These controls clear the external access/deploy blocker; t003 remains pending for its full journey and newly added repository-card scope. No whole-milestone completion is claimed.

The initial implementation shipped in c293ab9c1 and the TanStack useHydrated refactor in 21029d403. The prior source worker recorded passing dashboard format/lint/6375 tests/build and real renderToString → hydrateRoot clock/zone regressions for those two consumers. Those historical checks are not claimed to validate the added card implementation.

**Previous pre-repair failure (2026-10-20):** unmodified RepositoryListItem still computes clock-dependent text and a runtime-zone title on initial render. At both widths a real startup delay changes its relative phrase, emits React418 and replaces the focused profile tree while other card labels remain stable. A narrow repeat needs only 11.586 seconds (13 → 14 minutes); an immediate-release control retains all nodes/focus. Separately, Kiritimati retains the server-zone title on all 12 initial public cards while 12 newly mounted cards have correct titles. See the appended production controls in [FINDINGS.md](./FINDINGS.md). This extends the same open hydration finding; the finding-group count is unchanged.

## Repository-card deployment verification

**Unblocked 2026-10-22** — matching repaired RepositoryListItem is deployed. Fresh native-focus held-startup controls at1440/390 cross a real relative-age boundary and preserve every original card/time node and focused control without React418. Stable-window controls pass, and all initial/expanded titles agree across both widths × UTC/Kiritimati. t003 is complete using these new controls plus its previously recorded commit/activity/locale/navigation evidence. t009/t010 and final closeout remain open. [FINDINGS.md](./FINDINGS.md) retains details and the old blocker. Independent vertical startup restoration now has [963](../../963.md); it does not undo the proven timestamp/node repair and is not silently treated as fixed here.

## Closeout — 2026-10-22

Every definition-of-done item holds:
- **Commit, activity and card hydration.** Real `renderToString` → `hydrateRoot` regressions for all three consumers cover an age boundary, a matching window and a UTC/Kiritimati day change: `commit-metadata-hydration`, `profile-activity-hydration` and `repository-list-item-hydration`. Each fails against its unfixed source.
- **Native behaviour.** Deployed held-startup controls at 1440/390 keep the original nodes and focus without React418, and the exact titles, AX name and keyboard tooltip agree with the browser zone and language ([t003](./done/t003.md), [FINDINGS](./FINDINGS.md) §5–6 and the 2026-10-22 record).
- **Shared mechanism.** [t009](./done/t009.md) moved it into one `useHydratedTime()` with unchanged output.
- **Gates.** [t010](./done/t010.md) records format/lint/test (6706)/build passing on the closing revision.
- **Scope.** No API, clock override, ticker, dependency, credential or hosted-content change. The five other relative-time consumers remain audit-only.
- **Limits.** Native title popups, speech, other engines and live Starred cards remain unverified ([t006](./done/t006.md)).
