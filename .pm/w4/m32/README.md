# w4 · m32 — Preserve valid ledger dates across browser timezones

**Worker:** worker1 **Goal:** a valid Gregorian ledger date remains enterable regardless of whether the browser timezone ever observed that civil day **Status:** todo (t001–t004 done)

## Reproduced problem

**Severity:** minor. Production `https://beancount.io`, 2026-10-20, QA-owned headless isolated Chromium 155.0.8059.85, English/light, authenticated disposable synthetic ledger. Fresh 1440×1000 UTC and Pacific/Apia contexts; repeated Apia at 390×844. No entry was submitted and every temporary context was closed. Local main `c5e4cd11a`; the deployed parser source exactly matches local.

1. Open `/ledger/<qa-owner>/<synthetic-ledger>/journal?action=new-entry`, with the default Transaction tab selected. Enter `2011-12-30` in Date and blur.
2. In UTC it displays `12/30/2011`, has no invalid attribute and has no validation alert.
3. In Pacific/Apia the same ISO input stays `2011-12-30`, has `aria-invalid=true` and shows **Invalid input**. A fresh narrow form with localized `12/30/2011` gives the same refusal.
4. Correcting it to `2011-12-31` clears the error and displays `12/31/2011`. This is not an incomplete-input or impossible-February control.
5. In a separate Apia browser upload the two-row CSV below to Smart Import, without choosing AI or submitting. It previews **2 Valid** and Configure retains both `12/30/2011` and `12/31/2011`. The existing civil-date import fix works.

   ```csv
   Date,Payee,Description,Amount
   2011-12-30,qa-20261020-skipped-day,qa-20261020 calendar-only control,-1.25
   2011-12-31,qa-20261020-next-day,qa-20261020 following day,-2.50
   ```

Independent GraphQL Journal control with `time:"2011-12-30"` returns HTTP 200, total 0 and no error. That proves accepted filter syntax, not an accepted entry write. In the actual browser `new Date(2011,11,30)` is day 30 in UTC and day 31 in Apia. The installed date-fns control under `TZ=Pacific/Apia` likewise parses `2011-12-30` then formats it as `2011-12-31`.

## Cause and repair boundary

`dashboard/src/common/components/ui/date-picker-utils.ts:113–118` parses against a local `new Date()` reference and accepts only a matching local format round trip. The browser timezone's skipped day normalizes forward and fails that check, although it is a valid Gregorian bookkeeping date. `date-picker.tsx:37–39` exposes local Date values, and all seven forms retain that representation and serialize with local formatting. Merely loosening the round-trip comparison would silently select the following day.

Preserve calendar-day identity independently of local instants through typed validation, selected value, display and serialization. A canonical date-only value or equivalent civil-day representation must survive the picker/form boundary; adapt the calendar deliberately while retaining local **Today**, locale-specific date order, strict invalid-date rejection and ISO fallback. Keep API payloads as their existing `YYYY-MM-DD` strings. Reuse existing date utilities where suitable without introducing cross-feature imports or a second independent parser. Do not change the machine timezone, substitute day 31, accept a normalized wrong day or bypass validation.

The seven searched integrations are Journal Transaction, Balance, Note and Account; Accounts OpenAccountDialog; Budget AddBudgetDialog; ReceiptReviewForm. Only Journal Transaction was exercised live. Their source uses the same shared picker/local Date contract; other live forms and receipt parsing remain unverified. Coordinate w4/239's separate valid-then-invalid draft synchronization repair in the shared picker.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Preserve civil-day identity in the shared picker — **DONE** | 65m | — |
| t002 | Carry exact date-only values through all seven forms — **DONE** | 55m | t001 |
| t003 | Adoption surface — check date-entry promises and guides — **DONE** | 15m | t002 |
| t004 | Simplify the changed date flow — **DONE** | 15m | t003 |
| t005 | Verify real timezone and form regressions | 55m | t003 |
| t006 | Close out and archive the milestone | 15m | t004, t005 |

Estimated 220 minutes across coordinated shared-control and caller changes, so this exceeds the sub-hour inbox-note limit.

## Definition of done

- [ ] Fresh UTC and Apia browsers accept ISO and localized `2011-12-30` in the actual Journal form at desktop and narrow widths, with display and prepared payload preserving that exact Gregorian day.
- [ ] All seven picker integrations preserve date-only identity; receipt-prefilled canonical dates do not round-trip through an unrepresentable local midnight.
- [ ] Invalid calendar dates and incomplete input remain invalid, with linked error semantics; valid-then-invalid, clearing, reset, locale changes and reopening retain their intended contracts, including w4/239.
- [ ] Calendar selection, month/year navigation, keyboard access and local Today remain coherent. Ordinary UTC/Los Angeles date entry and existing CSV calendar controls keep working.
- [ ] No API/schema/dependency or OS timezone change is required; the actual browser/form regressions and dashboard format/lint/test/build pass.

## Dedupe and evidence

Searched all board states for Apia, skipped civil days, `2011-12-30` and DatePicker. Completed w3/141 (`008aca68`) repaired only CSV calendar arithmetic; its live preview/Configure controls pass here. Completed w3/m24 repaired permissive/shifted ISO typing through local strict dates, and w3/m42 added locale date order; neither covered a civil day absent in the browser zone. w4/239 concerns losing invalid drafts after a valid edit, a different sequence. Targeted parser history contains no civil-day representation repair. No overlapping open item was found.

Production `date-picker-DHE1-1Cn.js.map` serves `date-picker-utils.ts` SHA-256 `393081ad5d3bf5f5e76f47e91398702a372e3e4b22f32dbc138fad9fe98f45ac`, exactly matching local source. Ignored evidence under `dashboard/tmp/qa-20261020/dashboard-loop/`: `date-picker-skipped-day-control.json`, `date-picker-skipped-day-390.png`, `qa-20261020-apia.csv`. No actual write, API date-serialization capture, other engine or screen-reader speech is claimed; these are implementation verification targets. No product fix or tests were added during QA.

## Source + Goal linkage

- **Source:** continuous dashboard QA requested by the user for w4, 2026-10-20; fresh browser reproductions and local/deployed parser comparison above.
- **Goal linkage:** A2 — Frictionless onboarding: importing historical bookkeeping and manually entering its dates must agree across readers' browser timezones.
- **Expected outcome:** a person in a timezone with a skipped historical day can enter that valid ledger date without changing browser settings or switching to CSV.
- **Why now:** strict local-Date validation leaves a reproducible gap after the earlier calendar fixes; changing the shared value contract requires coordinated caller verification.
- **Adoption surface:** included because the shared control is exposed by seven entry workflows; review existing guidance without inventing a new public API or migration procedure.
