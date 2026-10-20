# w4 — General adoption worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty. Existing milestones retain their historical order and source.

## Inbox

- [232 — Apply the newer same-date budget target](./232.md) — major; dashboard QA, 2026-10-20.
- [233 — Report Budget deletion read/write failures](./233.md) — minor; dashboard QA, 2026-10-20.
- [234 — Execute BQL against current ledger data](./234.md) — major; dashboard QA, 2026-10-20.
- [235 — Load Budget directives beyond the first journal page](./235.md) — major; dashboard QA, 2026-10-20.
- [236 — Name the out-of-date ledger Refresh action](./236.md) — minor; dashboard QA, 2026-10-20.
- [237 — Keep public-page context through header sign-in](./237.md) — minor; dashboard QA, 2026-10-20.
- [238 — Return Accounts and Journal focus after successful writes](./238.md) — minor; dashboard QA, 2026-10-20.
- [239 — Keep invalid date drafts after valid edits](./239.md) — minor; dashboard QA, 2026-10-20.
- [240 — Name file-view Edit at narrow widths](./240.md) — minor; dashboard QA, 2026-10-20.
- [241 — Complete file saves without discarding newer edits](./241.md) — major; dashboard QA, 2026-10-20, pending-edit loss reproduced.
- [242 — Name Documents, Collaborators, Errors and Import Preview tables](./242.md) — minor; dashboard QA, 2026-10-20, populated/loading/empty controls scoped.
- [243 — Keep narrow Documents columns readable](./243.md) — minor; dashboard QA, 2026-10-20.
- [244 — Preserve fragments in native guest sign-in links](./244.md) — minor; dashboard QA, 2026-10-20.
- [245 — Name imported amounts with their normalized preview value](./245.md) — minor; dashboard QA, 2026-10-20.
- [246 — Keep loaded history pages while selecting a commit](./246.md) — minor; dashboard QA, 2026-10-20.
- [247 — Keep Create File from discarding edits accepted while pending](./247.md) — major; dashboard QA, 2026-10-20.
- [248 — Preserve committed file writes when folder refresh fails](./248.md) — minor; dashboard QA, 2026-10-20, Upload and Create File.
- [249 — Compose filter changes while report reads are pending](./249.md) — minor; dashboard QA, 2026-10-20.
- [250 — Protect standalone entry source drafts when leaving](./250.md) — minor; dashboard QA, 2026-10-20.
- [251 — Follow the new entry identity after a source save](./251.md) — minor; dashboard QA, 2026-10-20.
- [252 — Expose filtered active options in account and ledger pickers](./252.md) — minor; dashboard QA, 2026-10-20, both cmdk consumers live-reproduced.
- [253 — Preserve query cards and focus when history reorders](./253.md) — minor; dashboard QA, 2026-10-20.
- [254 — Preserve BQL source precision in chart tooltips](./254.md) — minor; dashboard QA, 2026-10-20.
- [255 — Keep input focus after accepting a combobox suggestion](./255.md) — minor; dashboard QA, 2026-10-20.
- [256 — Preserve unsaved New Entry fields across type changes](./256.md) — minor; dashboard QA, 2026-10-20.
- [257 — Offer an in-place retry when General Settings cannot load](./257.md) — minor; dashboard QA, 2026-10-20.
- [258 — Use the SVG MIME type in file previews](./258.md) — minor; dashboard QA, 2026-10-20.
- [259 — Reject new drops while an upload batch is pending](./259.md) — minor; dashboard QA, 2026-10-20, DOM drop coverage.
- [260 — Allow downloading existing zero-byte files](./260.md) — minor; dashboard QA, 2026-10-20.
- [261 — Keep switch states visible in forced colors](./261.md) — minor; dashboard QA, 2026-10-20.
- [262 — Keep Journal, Account, Overview and Files row focus visible in forced colors](./262.md) — minor; dashboard QA, 2026-10-20.
- [263 — Resolve file jumps with tab-separated Git headers](./263.md) — minor; dashboard QA, 2026-10-20.
- [264 — Make Try Again recover failed ledger child pages](./264.md) — minor; dashboard QA, 2026-10-20.
- [265 — Keep financial text and private paths out of GA4 automatic events](./265.md) — major; dashboard QA, 2026-10-20; stream-editor completion dependency.
- [266 — Disable import and receipt file pickers until hydration](./266.md) — minor; dashboard QA, 2026-10-20.
- [267 — Keep Trial Balance reconciliation independent of display signs](./267.md) — major; dashboard QA, 2026-10-20.
- [268 — Preserve an existing UTF-8 BOM when saving text files](./268.md) — minor; dashboard QA, 2026-10-20.
- [269 — Preserve Markdown blocks without a language label](./269.md) — minor; dashboard QA, 2026-10-20.
- [270 — Remove the unsupported blank transaction status](./270.md) — minor; dashboard QA, 2026-10-20.
- [271 — Distinguish a real event type all from All Types](./271.md) — minor; dashboard QA, 2026-10-20.
- [272 — Validate saved BQL history before rendering](./272.md) — minor; dashboard QA, 2026-10-20; controlled corrupted-cache recovery.
- [273 — Show the active command-picker option in forced colors](./273.md) — minor; dashboard QA, 2026-10-20.
- [274 — Preserve account-search focus through retry](./274.md) — minor; dashboard QA, 2026-10-20.
- [275 — Distinguish failed ledger-switcher reads from empty results](./275.md) — minor; dashboard QA, 2026-10-20.
- [276 — Refuse lossy text-file editing for unsupported byte encodings](./276.md) — minor; dashboard QA, 2026-10-20.
- [277 — Preserve years below 100 in CSV import date displays](./277.md) — minor; dashboard QA, 2026-10-20.
- [278 — Refuse CSV decoding that replaces source characters](./278.md) — minor; dashboard QA, 2026-10-20.

## Milestones

- [ ] **m37** — [Resolve README file links from their source path](./m37/README.md) (6 tasks) ← dashboard QA, 2026-10-20; minor, rendered file-link context and native hrefs.

- [ ] **m36** — [Preserve commit and profile activity timestamps through hydration](./m36/README.md) (7 tasks) ← dashboard QA, 2026-10-20; minor, commit/profile focus and commit browser-zone names.

- [ ] **m35** — [Keep form fields usable when suggestions fail](./m35/README.md) (6 tasks) ← dashboard QA, 2026-10-20; minor, four form suggestion wrappers.

- [ ] **m34** — [Resolve multiline entry sources without splitting quoted strings](./m34/README.md) (6 tasks) ← dashboard QA, 2026-10-20; minor, ledger source resolution.

- [ ] **m33** — [Keep New Entry drafts safe during submission](./m33/README.md) (6 tasks) ← dashboard QA, 2026-10-20; major, pending edits and late completion.

- [ ] **m32** — [Preserve valid ledger dates across browser timezones](./blocked/m32/README.md) (6 tasks) ← dashboard QA, 2026-10-20; minor, shared picker and seven form integrations. — **blocked:** fix shipped in `a48655dd6`; awaiting deployed UTC/Apia browser verification

- [x] **m31** — [Bound authentication abuse without losing account recovery](./done/m31/README.md) (11 tasks) ← user-approved rate-limit review and `$pm` / `$loopx w4`, 2026-10-19

- [x] **m29** — [Explore public examples before signing in](./done/m29/README.md) (9 tasks) ← approved `/pm-brainstorm for w4` candidate 1, 2026-09-27; mobile, ~4–5h implementation plus standing closing tasks

- [x] **m28** — [Locale-aware plurals on both clients](./done/m28/README.md) (8 tasks) ← promoted w4/187, filed from m27's wording deviation, 2026-09-26

- [x] **m27** — [Say which prices are stale, and only when they are](./done/m27/README.md) (7 tasks) ← user design review of m26's headline, 2026-09-26

- [x] **m26** — [Value Home and Accounts at market value, and say so on web and mobile](./done/m26/README.md) (10 tasks) ← user decision 2026-09-26 in a PM review of the Home net-worth basis; supersedes m11's display rules 1–2 and folds in w4/027 and w4/068

- [x] **m25** — [Reach the Latin-script locales with a half-translated guard](./done/m25/README.md) (7 tasks) ← promoted w4/157, filed from the w4/m24/t010 review, 2026-09-20

- [x] **m24** — [Repair the Ukrainian catalogs' first-word find/replace damage](./done/m24/README.md) (12 tasks) ← promoted w4/152, filed while closing w4/149, 2026-09-20

- [x] **m23** — [Prevent native authentication forms from putting passwords in URLs](./done/m23/README.md) (6 tasks) ← repeated dashboard QA, 2026-09-18

- [x] **m22** — [Expose read-only state in Monaco readers](./done/m22/README.md) (6 tasks) ← promoted w4/102 with Entry Context evidence, repeated dashboard QA, 2026-09-17

- [x] **m21** — [Preserve amounts and units in overview charts](./done/m21/README.md) (7 tasks) ← repeated dashboard QA, 2026-09-17

- [x] **m20** — [Name Budget, Commodities, Statistics and Settings tables](./done/m20/README.md) (6 tasks) ← promoted w4/091 with Statistics evidence, repeated dashboard QA, 2026-09-17

- [x] **m19** — [Preserve URL fragments in login continuations](./done/m19/README.md) (6 tasks) ← repeated dashboard QA, 2026-09-17

- [x] **m18** — [Make complete BQL cell values readable](./done/m18/README.md) (6 tasks) ← promoted w4/078 with PRINT evidence, repeated dashboard QA, 2026-09-17

- [x] **m17** — [Keep profile search updates from hijacking ledger navigation](./done/m17/README.md) (6 tasks) ← repeated dashboard QA, 2026-09-17

- [x] **m16** — [Preserve statement chart selection through report reads](./done/m16/README.md) (6 tasks) ← repeated dashboard QA, 2026-09-17

- [x] **m15** — [Associate authentication validation errors with their fields](./done/m15/README.md) (6 tasks) ← promoted w4/082, repeated dashboard QA, 2026-09-17

- [x] **m14** — [Restore truthful Catalan navigation and Journal labels](./done/m14/README.md) (6 tasks) ← from repeated dashboard QA, 2026-09-17

- [x] **m1** — Download Balance Sheet and P&L as CSV or print-ready PDF (9 tasks) ← from financial-report export PM research and `/pm` handoff, 2026-08-15
- [x] **m2** — Cash flow report: statement page, charts, exports, account status (10 tasks) ← from `dashboard/docs/ADR002-cash-flow-report.md`, 2026-08-20
- [x] **m3** — Ledger-declared cash-flow roles (`cash-flow-role` metadata) (10 tasks) ← from `dashboard/docs/PRFAQ-cash-flow-ledger-classification.md`, 2026-08-25

- [x] **m4** — Mobile ledger discovery and starred ledgers (10 tasks) ← from user-approved pm-brainstorm 2026-09-05
- [x] **m5** — Ledger links open in the app (10 tasks) ← from `/pm-brainstorm for w4` 2026-09-08; user approved all four
- [x] **m6** — Create a ledger from mobile (8 tasks) ← from `/pm-brainstorm for w4` 2026-09-08; user approved all four
- [x] **m7** — Screen-reader pass on the mobile core journeys (9 tasks) ← from `/pm-brainstorm for w4` 2026-09-08; user approved all four
- [x] **m8** — [Localized Google Play listing from the canonical metadata](./done/m8/README.md) (8 tasks) ← from `/pm-brainstorm for w4` 2026-09-08; user approved all four
- [ ] **m9** — [`bea price fetch`: keep commodity and currency prices current through upstream bean-price](./blocked/m9/README.md) (9 tasks) — **blocked:** needs a decision to re-scope onto the shipped `bea price` passthrough or drop. ← from `/pm-brainstorm for w4` 2026-09-10; user handed items 1, 6, 7 to `/pm` 2026-09-11 (issue 176)
- [ ] **m10** — [GitHub contributor front door: issue and PR templates, security policy, code of conduct, seeded good first issues](./blocked/m10/README.md) (9 tasks) — **blocked:** forms, PR template, and CI check shipped; needs the security reporting channel, approval for labels/contributor issues, and signed-in issue-chooser verification; issue176 already has the maintainer reply. ← from `/pm-brainstorm for w4` 2026-09-10; user handed items 1, 6, 7 to `/pm` 2026-09-11
- [x] **m11** — [Mobile says what a converted balance means: units for commodities, labelled cost basis, disclosed omissions](./done/m11/README.md) (9 tasks) ← promoted w4/016 with w4/027 folded in; user approved `/pm-brainstorm for w4` item 2 and its display rule, 2026-09-15
- [x] **m12** — [Make mobile's `lint:deadcode` see unused GraphQL documents and test-only modules](./done/m12/README.md) (7 tasks) ← promoted w4/025; user approved `/pm-brainstorm for w4` item 4 and its allowlist recommendation, 2026-09-15

- [x] **m13** — [Preserve ledger pages through loading and hydration](./done/m13/README.md) (6 tasks) ← repeated dashboard QA, promoted w4/073, 2026-09-17

## Dropped

- ~~**016**~~ — Commodity accounts are shown as an unlabelled USD cost basis — and a commodity with no cost renders as $0.00 — dropped 2026-09-26: promotion to [m11](./done/m11/README.md) completed; the milestone's verification record carries the outcome, and w4/m26 superseded its valuation basis.

- ~~**188**~~ — Type-check `count` for dashboard plural keys — dropped 2026-09-26: folded into [m28](./done/m28/README.md) as t008, since m28's definition of done already requires it.

- ~~**187**~~ — Locale-aware plurals on both clients — dropped 2026-09-26: promoted to [m28](./done/m28/README.md), preserving the note's scope; the work spans two packages and exceeds one hour.

- ~~**068**~~ — Mobile valuation toggle: cost, market value, or units per ledger — dropped 2026-09-26: superseded by [m26](./done/m26/README.md). Home and Accounts now value at market and show the cost basis beside the figure, so a per-ledger toggle is no longer planned; the web report pages keep their existing selector.

- ~~**027**~~ — "Net Worth" is a cost basis, and nothing on screen says so — dropped 2026-09-26: superseded by [m26](./done/m26/README.md). The user chose this note's option 2 (value at market and disclose stale prices) over option 1, which m11 had shipped; m26 carries the note's evidence and acceptance.

- ~~**102**~~ — Source-viewer read-only accessibility state — dropped 2026-09-17: promoted to [m22](./done/m22/README.md), preserving original evidence and adding Entry Context plus fallback-mode scope; shared integration and checks exceed one hour.

- ~~**091**~~ — Budget/Commodities table identities — dropped 2026-09-17: promoted to [m20](./done/m20/README.md), preserving original evidence and adding all three Statistics tables; coordinated repair and checks exceed one hour.

- ~~**078**~~ — BQL inventory clipping — dropped 2026-09-17: promoted to [m18](./done/m18/README.md), preserving the original evidence and adding PRINT multiline values; expanded implementation and verification exceed one hour.

- ~~**082**~~ — Sign-in and recovery error associations — dropped 2026-09-17: promoted to [m15](./done/m15/README.md), preserving the evidence and adding independently reproduced registration fields; the expanded repair now exceeds one hour.

- ~~**073**~~ — Journal shared-filter page reset regression — dropped 2026-09-17: superseded by [m13](./done/m13/README.md), which preserves the original evidence and adds the independently reproduced Accounts typing failure at the same pending boundary.

- ~~**025**~~ — Seven dead GraphQL operations and a 19-case test for a hook that doesn't exist, all invisible to `lint:deadcode` — dropped 2026-09-15: promotion to w4/m12 completed ([done/m12](./done/m12/README.md)); the operations, the test-only module and the pinned strings are deleted, and `yarn lint:deadcode` now catches both shapes.
- ~~**065**~~ — German is the only locale that leaves "YTD" untranslated — dropped 2026-09-14: not a miss but a recorded choice. `mobile/src/translations/__tests__/known-gaps.ts` lists `rangeYTD` in German's `SAME_AS_ENGLISH` entry with the reason "Range chips: M reads as Monat, and YTD is the standard term in German finance UIs", and the locale-integrity suite enforces it. Replacing it needs a native speaker's call, which the note itself deferred (SJB or JTD).
- ~~**018**~~ — m5 follow-up: ledger links do not open the app in production — dropped 2026-09-14: duplicate of `w4/blocked/001` ("Set hosted APP_LINKS env so AASA stops 404ing"), which waits on the same hosted `APP_LINKS_APPLE_TEAM_ID` / `APP_LINKS_ANDROID_SHA256` configuration. Its warm and cold repros, the deliberate unset-env 404, and its extended acceptance (JSON content type, validators, the deferred physical-device check) were appended to `blocked/001.md`.
- ~~**012**~~ — Extends w3/217: on a billion-scale ledger the Accounts balance itself is truncated — dropped 2026-09-14: duplicate of the open `w3/217` ("Keep Accounts row identities readable beside large balances"), which owns the same `AccountTable` row and cause; the note itself asked to be folded in rather than fixed separately. Its severity raise to major, the AX1 and 19-character-balance acceptance, and its evidence were appended to `w3/217`.
- ~~**057**~~ — Money formatter rounds every amount to 2 decimals — dropped 2026-09-13: duplicate of the open `w3/189` ("The account journal rounds a posting the transactions list shows in full"), which identifies the same `groupThousands()` `toFixed(2)` cause at the same lines, carries the full call-site list and the product decision, and predates it. The two genuinely new observations — the `w4/016` fix-ordering interaction and the undocumented number-locale pin — were appended to `w3/189` instead.

## Execution notes

Blocked milestones live under `blocked/` with their reason and unblock condition in a `## Blocked` section; they keep their task IDs and return to `wN/mN/` when work can resume.

## Blocked inbox follow-up

- [ ] [096 — Verify protected-route login history](./blocked/096.md) — blocked on a current protected-query trigger and native-toolbar Back reproduction; original Import/History triggers retired, automated traversal alone is insufficient.
