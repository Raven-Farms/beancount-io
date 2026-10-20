# Commit and profile activity timestamp hydration findings

**Minor, dashboard.** Production https://beancount.io, 2026-10-20, local main c5e4cd11a, deployed main-D9qWGMxD.js; full deployed revision unverified. QA-owned isolated headless Chromium155.0.8059.85, English/light, 1440×1000 and390×844. Authenticated owner reads of the designated synthetic ledger. Browser time zones are explicit emulation; OS settings and clocks are untouched.

The existing QA-prefixed 1200-line text fixture was created and guard-deleted before these history reads. Its historical commit320bf9f6a0655c04dfd23d6fd225d945fb3a95ef supplies a fixed author instant, 2026-10-20T17:19:43Z. These probes select no file, invoke no mutation, consume no AI and make no further hosted changes. Public route placeholders: /ledger/<qa-owner>/<synthetic-ledger>/commit/<fixture-sha>.

## 1. A relative-age boundary replaces the focused control

An unmodified desktop load produced one React418 warning while large-diff navigation otherwise worked. That observation alone was not filed as a functional bug. The following controlled reproductions establish the failure:

1. Hold only delivery of the real main-D9qWGMxD.js response. Render the genuine production server HTML; do not replace any response body, API result or timestamp, and do not change the clock.
2. Use native Shift+Tab/Tab to focus the visible Load Large Diff button. It is focused and focus-visible. Retain a DOM identity reference without changing the component.
3. Release the actual script after the relative-age phrase crosses its real-time rounding boundary. At desktop, the server label is 6 minutes ago and the initial client label is 7 minutes ago. At narrow width, it changes from 7 to8 minutes ago.
4. Both cases emit React418 text mismatch, disconnect the original button and replace it; the settled active element is BODY. The reader loses keyboard position without activating a command. The underlying commit, file list and author instant have not changed.
5. Working controls at both widths release startup within a stable phrase: 7→7 minutes at desktop and9→9 at narrow width. The narrow control includes about7 seconds of held delivery. Both retain the same connected button and its keyboard focus, with zero page errors. Thus startup delay by itself does not require this replacement.

These are explicit controlled initialization-latency cases against real production responses, not claims that every natural load fails. They use actual time and native focus; the harness does not invoke a React handler. React's [official error418 explanation](https://react.dev/errors/418) describes server/client rendering disagreement causing client-tree regeneration and identifies changing clock input as a possible cause. The retained DOM/focus evidence establishes the practical effect here.

CommitMetadata at features/git/commits/components/commit-metadata.tsx:36–37,91 computes its visible relative phrase on each render. common/hooks/use-date-locale.ts:21–27 delegates to common/lib/format/format-relative-time.ts:10, which calls formatDistanceToNow. Installed date-fns4.1.0 forwards through constructNow to Date.now; that installed dependency trace is local, with exact deployed dependency revision unverified. The real-time browser experiment independently confirms the differing server/client phrases.

## 2. The exact accessible name retains the server time zone

An independent fresh 390px Pacific/Kiritimati context captures the actual server-rendered time element, then releases startup immediately:

- datetime stays2026-10-20T17:19:43Z.
- SSR aria-label is Oct20,2026,5:19:43PM UTC.
- After hydration, the original time node remains connected and retains that UTC label.
- The browser's own active-language Intl output and actual keyboard-opened tooltip are Oct21,2026,7:19:43AM GMT+14.

A separate natural production load at1440px, without script delay, repeats the same label/tooltip disagreement with zero page errors. The native accessibility tree reports role=time, ignored=false and the retained Oct20 UTC accessible name, while the keyboard tooltip shows Oct21 GMT+14. A natural UTC desktop control has matching attribute, computed name, tooltip and browser Intl output. This is a retained server-zone label, not a changed instant or claim that UTC itself is an invalid representation.

CommitMetadata:38–42 computes exactTime using Intl with the active language and the runtime's default zone. It passes the string into the initial SSR aria-label at line88. The client computes a different browser-zone value, but initial attribute mismatch does not update the retained DOM label; the subsequently mounted tooltip uses the correct client string. Coordinate stable initial rendering and an actual post-hydration attribute update. Merely supplying the right client render prop is insufficient, as the real DOM/AX control shows.

## Bounded repair and preservation

Keep server and initial client timestamp output deterministic, then update relative/browser-zone representations after hydration without replacing the timestamp or neighboring controls. A local useHydrated/stable initial-render approach may reuse existing repository conventions. Preserve readable SSR output, the exact author instant, active-language date-fns/Intl behavior, actual browser zone, tooltip keyboard access and responsive layout. Do not hardcode UTC as the final browser label, globally override Date, add an age ticker/dependency, silence warnings without retaining DOM/focus, or disable unrelated controls to hide the symptom.

The relative-time helper has eight production consumers: CommitMetadata, CommitListItem, What's New list, Plaid bank item, feed card, dashboard sidebar, repository list item and profile activity. CommitMetadata is proved for both failures above; the independently reproduced ProfileActivity relative/focus failure is documented below. CommitMetadata's one production caller is CommitDetail, shared by direct detail/history layouts. The six remaining consumers remain audit scope, without a global redesign. A desktop history-row title was not available in the retained zone control, so there is no separate history-title finding.

## Dedupe and deployment proof

All board states/open milestones and targeted history were checked for relative time, hydration, clock boundaries, timestamps and focus. Completed w3/m22 (48720f451) localizes date-fns/calendar consumers and preserves locale-loading isolation; that repair remains present. Completed w4/227 (1bac59231) localizes exact commit strings and preserves browser-zone formatting in mounted/client checks; its SSR attribute lifecycle was not verified. These are remaining initial-render cases. W4/266 concerns trusted activation before picker handlers attach; here merely focusing a control is lost when clock text mismatches, and the independent exact-name case happens after hydration. W4/264's loader retry and246's history continuation are different causes. No pending overlapping timestamp-hydration repair was found.

Actual production source maps match local bytes:

| Source | Map | SHA-256 |
| --- | --- | --- |
| commit-metadata.tsx | commits-split-view-CGTross5.js.map | f07d2a4189304ac5735680c3478595b12740b20a90ccfa44b1f085be617a05ee |
| use-date-locale.ts | use-date-locale-DEx5L3T7.js.map | 51f6927c43966a1826b5ec1279b6a453ec2f3960546442620778a96419919678 |
| format-relative-time.ts | same locale map | aa943dc5bbc8e1007f8b29ce23a62ba168db93e50c28461ded9039f0693adf8b |

## Evidence and cleanup

Ignored dashboard/tmp/qa-20261020/dashboard-loop/ contains commit-timestamps-hydration-control.json (four boundary/stable controls, three zone controls and source maps), commit-hydration-boundary-control.json, commit-hydration-stable-window-390-control.json, commit-timestamp-zone-hydration-control.json and commit-hydration-source-maps.json. Paired commit-hydration-{cross-boundary,stable-window}-390.png were visually inspected: the failing case has no focused-button cue; the stable case retains it. Native DOM/AX records supply identity/name proof. Screenshots alone do not prove the timing.

All script gates were released and temporary contexts closed. Original main.bean remains the only file:2817 bytes, original blob f1a0b83c1aaf9608113c6bd3174bf7d2dab35407 and SHA-25677c3a591efd311e01d03d2f3a91f2919151c0fb0708e1abe1a10ce6ec7e29915. Main-file restoration was7ec77a71a5204f48942418ea9dd4e8c4309a1cad; the later text fixture was deleted in b6cacf4e852f0e306f57580b20623544c99b1a02 before these probes, with zero ledger errors. Main session history/theme/locale and OS settings are unchanged. No product fix, test change, commit or push. The six remaining relative-time consumers, actual speech, physical slow devices, additional locales/zones and repaired behavior remain unverified.

## ProfileActivity extension: the same clock boundary loses collection focus

A fresh accessible-name scan observed a React418 warning on `/ledger/open_ledger`; that observation alone did not establish its cause. Independent production SSR controls now prove ProfileActivity's clock text has the same failure mechanism:

- Fresh guest UTC/English1440×1000 and390×844 contexts hold only the unmodified main script's delivery. The real server HTML already contains18 time elements and the Show more ledgers button. Native Shift+Tab/Tab leaves that button focused and focus-visible before handlers attach. No control is activated.
- Release startup after an actual minute-rounding boundary. Desktop activity labels include35→36 minutes; narrow labels37→38. Their exact datetime instants remain unchanged. The narrow capture identifies each changed time inside `#profile-activity-list`; repository-card time labels do not change in these records.
- Both cases emit React418, disconnect all18 original time nodes and the focused collection button, and leave activeElement=BODY. The new button has the same purpose but is a different DOM node. Thus an activity timestamp removes the reader's keyboard place in a sibling section.
- Separate matching-window controls at both widths retain the original button, all18 original time nodes and native focus, with zero errors or changed relative strings. They hold delivery briefly and release within the same38-minute phrase. Startup and hydration themselves do not require replacement.

These are real browser/server clocks and real HTML/script/API bodies, with no clock stub, synthetic timestamp, fabricated response or API write. The desktop document reports no-cache and DYNAMIC without an Age header; this record does not attribute the failure to stale CDN HTML. Several activity labels cross in the desktop hold; no claim isolates a single activity as the only possible mismatch.

`dashboard/src/features/user-profile/components/profile-activity.tsx:120` calls the same useFormatRelativeTime→formatDistanceToNow chain during server/client render. It is rendered by UserProfilePage's shared profile tabs. Extend the bounded initial-render/hydrated transition to this proved consumer, preserving public discovery and unchanged activity instants. Do not add unproved repository-card or exact-title/time-zone repairs. The shared formatter still has six other consumers to audit; this is an extension of the existing clock/hydration finding, not another issue.

Targeted history/all-board searches found no separate profile activity hydration item. Completed w3/m22 localizes this consumer and remains intact; its formatting-language repair does not stabilize changing initial clock input. Fetched main18d61188 has no correction in ProfileActivity or the shared helpers. Actual `ledger._username-D9SkLCXX.js.map` exactly matches local ProfileActivity SHA-256 `52e46acf0ffaebb1fc35ffaed8dfb35bd594dbff6cb2663339686d467fbd6c88`.

Ignored evidence: `dashboard/tmp/qa-20261020/dashboard-loop/profile-timestamps-hydration-control.json`, desktop `profile-hydration-focus-{before,after}-1440.png`, and `profile-hydration-{boundary,stable}-{before,after}-{1440,390}.png` for recorded combinations. The narrow boundary before/after and stable focused crops were inspected. Native identity/focus records, rather than images alone, prove replacement. All four startup gates released and contexts closed; zero mutation or AI attempts, hosted changes or main-session preference/history changes. Profile exact titles/time zones, other locales/engines, natural failure frequency, physical devices and corrected code remain unverified.
