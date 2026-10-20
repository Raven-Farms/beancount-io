# w4 · m36 — Preserve commit and profile activity timestamps through hydration

**Worker:** worker1 **Goal:** Commit and profile activity timestamps hydrate without replacing a focused control; commit exact-time names agree with browser-zone tooltips. **Status:** todo

**Severity:** minor. **Estimate:** 175m across seven tasks, dashboard only.

## Tasks

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Stabilize initial commit relative-time rendering | 45m | — |
| [t002](./t002.md) | Synchronize the exact timestamp name after hydration | 25m | t001 |
| [t007](./t007.md) | Stabilize initial profile activity relative-time rendering | 30m | t001 |
| [t003](./t003.md) | Verify the timestamp and keyboard adoption surface | 15m | t002, t007 |
| [t004](./t004.md) | Simplify the changed timestamp lifecycle | 10m | t003 |
| [t005](./t005.md) | Prove SSR identity and timestamp correctness | 40m | t003 |
| [t006](./t006.md) | Close out and archive the milestone | 10m | t004, t005 |

## Definition of done

- [ ] A real server-rendered CommitMetadata hydrated across a relative-age label boundary retains the original timestamp and focused neighboring control, with no React418 recovery.
- [ ] A real public ProfileActivity hydrated across its relative-age boundary retains the existing profile tree and focused Show more ledgers button. Its unchanged activity instants display current relative labels without React418 recovery.
- [ ] Matching-window controls for both consumers also retain their original nodes/focus; readable SSR timestamps remain available.
- [ ] After hydration, the actual time element's accessible name and keyboard tooltip agree with active application language and actual browser time zone, including a UTC/Kiritimati calendar-day difference. The datetime instant never changes.
- [ ] Desktop/narrow, normal client navigation, locale switching, tooltip access and large-diff/file navigation continue working. No API, clock override, new dependency, credential or hosted-content change is needed.
- [ ] Meaningful real SSR/hydration regressions and dashboard format/lint/test/build pass. Record the tested build/target and distinguish local verification from production deployment.
- [ ] Source-only related consumers remain explicitly scoped; do not redesign every relative-time user or add an automatic age ticker.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. See [the live findings](./FINDINGS.md). **A2 — Frictionless onboarding:** a keyboard reader on a slow initial load must retain their place, and a commit's exact-time accessible name must describe the same local date as its tooltip. Commit and public-profile warnings led to independently controlled startup-delay reproductions at both widths, with matching-window controls. Both relative failures use the same live-clock helper; the separate exact-name failure remains proved only for CommitMetadata. Coordinated initial-render behavior, local consumer integrations, real hydration tests and browser verification exceed one hour. Adoption-surface verification includes public collection discovery as well as commit reading because these controls directly affect onboarding.

## Scope

Repair the independently reproduced CommitMetadata consumer, rendered by CommitDetail in direct/history layouts, and ProfileActivity, rendered by the public/ordinary profile page. Keep localized date helpers and exact source instants. The six remaining relative-time consumers, including repository-card timestamps, remain audit scope, not additional confirmed failures or required global rewrites. Profile title/time-zone behavior has not been verified and is not added to the commit-name repair. No product code has been changed by QA.
