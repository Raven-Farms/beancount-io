# w4 · m35 — Keep form fields usable when suggestions fail

**Worker:** worker1 **Goal:** A failed suggestions read leaves New Entry fields editable and offers recovery without restarting the draft. **Status:** blocked (t001, t002, t004, t005 done; t003 found a deployed retry-focus gap)

**Severity:** minor. **Estimate:** 145m across six tasks, dashboard only.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. **A2 — Frictionless onboarding:** a newcomer should be able to type a known payee, narration, account or currency when an optional suggestion request fails. The current wrappers replace the actual fields with error alerts and expose no retry. Fix the four independently reproduced wrappers and verify their shared consumers now, because a single transient request failure blocks ordinary entry without any ledger outage. Four components, caller preservation and real query/form regression coverage exceed one hour. Adoption-surface verification is included because the recovery controls and draft behavior are visible to users.

## Tasks

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Retain Payee and Narration fields on suggestion failure — **DONE** | 30m | — |
| [t002](./done/t002.md) | Retain Account and Currency fields with existing validation — **DONE** | 25m | t001 |
| [t003](./t003.md) | Verify the visible recovery and draft journey | 35m | t002 |
| [t004](./done/t004.md) | Simplify the changed field handling — **DONE** | 10m | t003 |
| [t005](./done/t005.md) | Prove query failure recovery and run dashboard checks — **DONE** | 35m | t003 |
| [t006](./t006.md) | Close out and archive the milestone | 10m | t003, t004, t005 |

## Fresh live reproduction

Production https://beancount.io, local main `c5e4cd11a`, QA-owned isolated headless Chromium 155.0.8059.85, English/light, designated disposable synthetic ledger. Each case uses a fresh owner context at 1440×1000 and 390×844. These are explicit browser-local network aborts, not evidence of a natural production outage. All mutations are guarded before transmission; none was attempted.

1. Open `/ledger/<qa-owner>/<synthetic-ledger>/journal?action=new-entry&directive=transaction`. Abort only the read-only GetLedgerPayees operation. The settled Transaction panel shows Connection problem guidance where Payee belonged; zero comboboxes named Payee and zero Retry/Try Again buttons exist.
2. Type `qa-20261020 preserved suggestion-failure draft` into the healthy Narration field. Remove the request fault. The mounted form keeps that narration, but Payee remains absent and the alert remains. Reload: a genuine successful Payees read restores the field, while the narration draft is empty.
3. Independently repeat with only GetLedgerNarrations aborted: Narration is absent, while Payee accepts a prefixed draft. Removing the fault leaves the same inaccessible field; reload restores it and clears the draft.
4. Independently open directive=note with only GetLedgerAccounts aborted. Note content remains editable, but Account is absent and Create Note Entry stays disabled. There is no retry; restoring the network alone does not restore Account. The root background and form issue separate account reads; both are recorded and aborted.
5. Independently open directive=balance with only GetLedgerCurrencies aborted. Amount accepts 49.70, but Currency is absent and cannot be edited. Reload restores its real default USD control. No Balance entry was submitted.

All four failures and successful reload controls reproduce at both widths. Other healthy fields and the dialog remain usable; the entire ledger is not unavailable. Missing Account and Currency are not assertions that their values may bypass validation or that a draft with other missing required fields must submit.

## Cause and repair boundary

The following independent wrappers return only Alert on query error, before their value/onValueChange-controlled Combobox:

- `common/components/ledger-comboboxes/payees-combobox.tsx:65–70`
- `common/components/ledger-comboboxes/narrations-combobox.tsx:65–70`
- `common/components/ledger-comboboxes/account-combobox.tsx:72–77`
- `common/components/ledger-comboboxes/currency-combobox.tsx:65–70`

Each healthy combobox permits custom text. These reads supply suggestions, while the draft is already owned by the parent form. The wrappers discard query refetch and expose no in-place recovery. Their initial loading skeletons are a separate state from this settled error.

Keep the actual controlled field usable on a suggestions failure, with honest localized guidance, unavailable/empty suggestions and an in-place retry. Preserve its accepted text, accessible name, error association and keyboard focus through retry/loading/success. A retry must not remount the whole dialog or reset its form. Successful recovery restores genuine current-ledger suggestions and removes the warning. Suppress retained/partial failed suggestions rather than presenting them as current data.

Preserve permissions, disabled state, exact values, custom-text and Enter/blur/Escape semantics, account prefix filtering, default currency and all independent validation. In particular, New Entry's separate GetLedgerAccountDirectives/useAccountAvailability behavior from completed w3/560 must remain intact, including closed/future accounts and explicit also-open. No API, dependency or cross-package change is needed.

## Callers, dedupe and deployment

Payee and Narration wrappers have one production consumer each: TransactionForm. Account is also used by New Entry Balance/Note/Transaction, Budget, importer Configure/mapping, receipt review and Plaid mapping/review. Currency is used by Transaction/Balance, Budget, importer Configure and receipt review. Only the recorded New Entry forms were live exercised for this failure; other consumers are shared-code regression scope. OperatingCurrencyCombobox and SourceFileCombobox have similar source branches, but no independent live failure was exercised; they are unverified audit scope, not confirmed findings in this milestone.

All board states were searched for the operation/component names and failed suggestions, autocomplete, retry and form fields. Completed w4/203 repairs optional report-filter attributes in LedgerSearchControls; that component is different and its manual fallback is present on main. Completed w3/498 supplies field names and w3/560 account availability; retain both. W4/255 concerns focus after a successful suggestion selection, m33 pending submission ownership, and 256 switching directive types. None repairs these four failed-read branches. History retains the error return from `af5339de0`; `fa3a0b9c3` forwards field identity without changing it.

Three actual HTTP200 production source maps match local sources exactly:

| source | source map | SHA-256 |
| --- | --- | --- |
| payees-combobox.tsx | ledger._ledgerOwner._ledgerName.journal-DFfgnGSN.js.map | `b3a4d459732f124d6d77a2916634d75d008e1005121d8f3f89459335456a921b` |
| narrations-combobox.tsx | same Journal map | `655162c9448f56de23a6c96d152616e3cdc5fb85e5164b3890c0079d5cafee6b` |
| account-combobox.tsx | account-combobox-DGppEH7D.js.map | `f28d046be97b2eab25b4cbb5aae64ed718c463b7b420613b5d31051156e88f03` |
| currency-combobox.tsx | currency-combobox-Dx-PAsMC.js.map | `b0a5ad352469bfa3b2f2e631624e728de7c18df3d3711b862602cbd2f5db7232` |

Deployed full revision is unverified; the four relevant implementations match this checkout, so this is not a missing local fix awaiting deployment.

## Evidence and limits

Ignored evidence under `dashboard/tmp/qa-20261020/dashboard-loop/`: `form-suggestions-payee-failure-control.json`, `form-suggestions-related-failure-control.json`, `form-suggestions-source-maps.json`, `payee-suggestions-failed-{1440,390}.png` and `form-{narration,account,currency}-suggestions-failed-{1440,390}.png`. The narrow Payee/Account and desktop Currency captures were visually inspected. JSON contains actual role snapshots, aborted operation counts, retained sibling drafts and real successful reload controls.

No ledger writes, product edits, new tests, commit or push. All temporary contexts/interceptors closed. Physical devices, other engines/locales, authz or application-error responses, retrying an already-edited field, non-New-Entry consumers and repaired behavior remain unverified.

## Definition of done

- [ ] All four live-reproduced failed-read cases retain their named manual fields, honest failure guidance and in-place recovery at desktop/narrow widths.
- [ ] Accepted form text and focus survive failed retry, retry loading and successful suggestions recovery without restarting New Entry.
- [ ] Suggestions remain correctly scoped; failed/partial reads do not display stale options.
- [ ] Existing account availability, exact decimal submission, permissions, disabled state and keyboard selection behavior pass meaningful controls.
- [ ] Actual query/form regression checks detect the original branches; dashboard native checks pass and evidence states deployment/platform limits.
- [ ] Tasks and milestone are archived through /pm only when the observable end state holds.

## Blocked

**Blocked 2026-10-20** — t003's live recovery journey (and therefore t006 Closeout) cannot run here.

- **Shipped baseline:** the dashboard commit that carries this block's preceding implementation (`fix(dashboard): keep suggestion fields usable when their read fails (w4/m35)`). Payee, Narration, Account and Currency wrappers keep the controlled Combobox mounted on a failed read, withhold options, and show a localized "Suggestions couldn't load. You can still type a value." notice (linked through `aria-describedby`) with an in-place **Try Again**; the skeleton is limited to the first load so a retry never remounts the field. `ledger-comboboxes/__tests__/suggestions-failure.test.tsx` drives each wrapper through real Apollo `MockedProvider` failure → failed retry → successful retry, asserting the same field node, kept text, no stale options and restored suggestions; all four fail against the old error-only branches. Dashboard format, lint, 6369 tests and build pass. Shared callers (Budget, importer, receipt, Plaid) receive the same contract with unchanged props; `OperatingCurrencyCombobox` and `SourceFileCombobox` keep their similar branches as unverified audit scope (no live failure was recorded for them). New Entry form integration still uses the existing mocked-combobox tests; no form-level failure test was added.
- **Blocker:** the DoD's 1440/390 live aborts of each operation need the deployed build and a timezone/network-controllable browser; this worker has no Chrome for Playwright and no authenticated stack.
- **Unblock:** after deploy, QA aborts GetLedgerPayees, GetLedgerNarrations, GetLedgerAccounts (Note) and GetLedgerCurrencies (Balance) one at a time at both widths, types into the still-present field, presses Try Again while failed and after restoring the network, and confirms the draft and focus survive and suggestions return. **Who:** the user (deploy) and the dashboard QA loop.

## Deployed verification 2026-10-20: retry focus still fails

The initial field-replacement failure is fixed in the served build. In fresh desktop 1440px and narrow 390px owner contexts, aborting GetLedgerPayees leaves the named Payee input enabled, with linked unavailable-suggestions guidance and Try Again. Type qa-20261020-kept-payee, use native Tab (past Clear) to focus Try Again, and Enter while the read is still aborted. Restore the network, reach Try Again again with native Tab/Enter, and let its real refetch succeed. The same input node retains the exact draft and healthy suggestions return (10 options after clearing the search), but focus ends on the enclosing New Entry dialog rather than the field or a useful continuation control. Both widths reproduce. An independent narrow repeat waits 800ms after completion and captures the same final dialog focus.

Failed-retry focus itself varies: the two-width sample ended on the dialog, while the settled repeat retained Try Again. One first-success-only sample ended with role=combobox, without recording the specific field identity; it is not evidence that every successful retry loses focus. The retained-text/healthy-options control is working, and clicking Payee restores its native input focus. The reproducible residual is the keyboard recovery sequence after a failed retry, not renewed field loss or data loss. No mutations were attempted; all writes were guarded and extra contexts closed.

use-suggestions-fallback.tsx renders the retry with loading=retrying and no completion focus handoff; the shared Button disables itself while loading, and the notice/button disappears on success. Combobox renders that notice below its field. The helper and Combobox source maps exactly match source at capture (1cdf076a0) (SHA-256 a9448e8c11c6133f1450c36f73dee50aa35fd7792b76ba606c6fe0ab4796658f and b2ac5fe51d83219653b0c59dc8b6a4bce73ae57eea5e57a3b1e3e2204adf4bba). A complete deployed Payees wrapper hash was not extracted. All four wrappers share this helper; only Payee's residual focus was independently exercised.

Finish a bounded focus handoff for these retry controls without remounting the field, losing text, reopening stale options or changing normal Tab behavior. Preserve logical field/retry focus through failed and pending attempts; when a successful retry removes its button, return focus to the associated field. Add a real Dialog/form userEvent Tab/Enter regression that observes activeElement. Existing suggestions-failure.test.tsx uses fireEvent.click and checks node/value preservation, so its passing assertions do not establish native focus recovery. Audit the other three helper consumers and complete the existing desktop/narrow four-operation verification in t003. No global focus manager, dependency or API change is needed; estimate adds 25m to that remaining task.

This extends the original m35 focus acceptance, with no duplicate issue or extra finding-group count. Completed 255 concerns ordinary option selection and 274 concerns the separate sidebar account-search retry. Ignored evidence under dashboard/tmp/qa-20261020/dashboard-loop: suggestions-retry-focus-control.json, suggestions-retry-focus-settled-control.json, suggestions-retry-focus-source-control.json and inspected suggestions-retry-after-{failure,success}-focus-390.png. The earlier suggestions-retry-focus-lost-390.png came from a first-success-only control and is excluded as failure evidence.

The previously missing deployed build/browser is now available, but the original focus-preservation unblock condition is not met. Keep this milestone and t003 blocked until the bounded retry-focus follow-up lands and the real four-wrapper journeys pass at both widths; the implementation follow-up can use the concrete evidence above. Closeout now explicitly depends on t003 as well as the prior initial implementation reviews. QA made no product fix.
