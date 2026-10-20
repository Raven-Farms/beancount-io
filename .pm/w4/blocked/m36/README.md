# w4 · m36 — Preserve commit and profile activity timestamps through hydration

**Worker:** worker1 **Goal:** Commit and profile activity timestamps hydrate without replacing a focused control; commit names and profile activity titles reflect the browser time zone. **Status:** blocked (t001, t002, t007, t004, t005 done; t003 needs a deployed browser check)

**Severity:** minor. **Estimate:** 185m across seven tasks, dashboard only.

## Tasks

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Stabilize initial commit relative-time rendering — **DONE** | 45m | — |
| [t002](./done/t002.md) | Synchronize the exact timestamp name after hydration — **DONE** | 25m | t001 |
| [t007](./done/t007.md) | Stabilize profile activity relative text and exact titles — **DONE** | 40m | t001 |
| [t003](./t003.md) | Verify the timestamp and keyboard adoption surface | 15m | t002, t007 |
| [t004](./done/t004.md) | Simplify the changed timestamp lifecycle — **DONE** | 10m | t003 |
| [t005](./done/t005.md) | Prove SSR identity and timestamp correctness — **DONE** | 40m | t003 |
| [t006](./t006.md) | Close out and archive the milestone | 10m | t004, t005 |

## Definition of done

- [ ] A real server-rendered CommitMetadata hydrated across a relative-age label boundary retains the original timestamp and focused neighboring control, with no React418 recovery.
- [ ] A real public ProfileActivity hydrated across its relative-age boundary retains the existing profile tree and focused Show more ledgers button. Its unchanged activity instants display current relative labels without React418 recovery.
- [ ] Matching-window controls for both consumers also retain their original nodes/focus; readable SSR timestamps remain available.
- [ ] ProfileActivity's five initial exact-time title attributes and client-expanded rows agree with the browser time zone after hydration, including a UTC/Kiritimati calendar-day difference; their datetime instants stay unchanged.
- [ ] After hydration, the actual time element's accessible name and keyboard tooltip agree with active application language and actual browser time zone, including a UTC/Kiritimati calendar-day difference. The datetime instant never changes.
- [ ] Desktop/narrow, normal client navigation, locale switching, tooltip access and large-diff/file navigation continue working. No API, clock override, new dependency, credential or hosted-content change is needed.
- [ ] Meaningful real SSR/hydration regressions and dashboard format/lint/test/build pass. Record the tested build/target and distinguish local verification from production deployment.
- [ ] Source-only related consumers remain explicitly scoped; do not redesign every relative-time user or add an automatic age ticker.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. See [the live findings](./FINDINGS.md). **A2 — Frictionless onboarding:** a keyboard reader on a slow initial load must retain their place, and exact-time information must describe the browser's local date consistently. Commit and public-profile warnings led to independently controlled startup-delay reproductions at both widths, with matching-window controls. Both relative failures use the same live-clock helper. The independent exact-attribute failures affect CommitMetadata's accessible name and ProfileActivity's native title; only the commit has the separately verified keyboard tooltip. Coordinated initial-render behavior, local consumer integrations, real hydration tests and browser verification exceed one hour. Adoption-surface verification includes public collection discovery as well as commit reading because these controls directly affect onboarding.

## Scope

Repair the independently reproduced CommitMetadata consumer, rendered by CommitDetail in direct/history layouts, and ProfileActivity, rendered by the public/ordinary profile page. Keep localized date helpers and exact source instants. The six remaining relative-time consumers, including repository-card timestamps, remain audit scope, not additional confirmed failures or required global rewrites. The profile title/time-zone reproduction belongs to its existing t007 integration; t002 remains the commit accessible-name repair. Profile native-tooltip rendering, physical speech and other locales remain unverified. No product code has been changed by QA.

## Blocked

**Blocked 2026-10-20** — t003's browser verification on a real server-rendered build (and therefore t006 Closeout) cannot run here.

- **Shipped baseline:** the commit `fix(dashboard): hydrate commit and profile timestamps without replacing them (w4/m36)`. A new `useHydrated()` (`useSyncExternalStore`, false on the server and the hydration render) lets CommitMetadata and ProfileActivity render the exact time in UTC — readable, clock- and zone-independent — on the server and the first client render, then switch in place to the relative age plus the browser-zone exact label/title. Real `renderToString` → `hydrateRoot` tests with a fake clock and `TZ` switch prove, for both components, that the time nodes and the focused copy / Show all activity button survive a relative-age boundary with no recoverable error, that the commit `aria-label` (also the tooltip text) and all five initial plus expanded profile titles move to Pacific/Kiritimati's 28 July while `datetime` is unchanged. Boundary and zone tests fail against the previous components; the profile stable-window control passes on both. Dashboard format, lint, 6375 tests and build pass. The six other relative-time consumers were not changed.
- **Blocker:** the DoD's desktop/narrow browser journey (held startup, tooltip and AX name, locale switch, large-diff navigation, profile collection search) needs a deployed or locally served SSR build and a browser with zone emulation; this worker has no Chrome for Playwright.
- **Unblock:** after deploy, QA repeats the FINDINGS.md startup-delay and UTC/Kiritimati reproductions at 1440 and 390 on a commit page and a public profile and confirms retained focus, current relative phrases, browser-zone names/titles and no React #418. **Who:** the user (deploy) and the dashboard QA loop.
