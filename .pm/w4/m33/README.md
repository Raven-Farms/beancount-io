# w4 · m33 — Keep New Entry drafts safe during submission

**Worker:** worker1 **Goal:** A successful entry submission must not erase text accepted afterward or close a later draft. **Status:** todo

**Severity:** major (browser-local draft loss). **Estimate:** 130m across six tasks, dashboard only.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. **A2 — Frictionless onboarding:** a person entering bookkeeping details should trust the active draft during a slow request. New Entry accepts more input and even a new dialog while an earlier submission is pending; that earlier success then removes the current work. Fix this now because ordinary network latency is enough to expose it. The repair spans the shared dialog's submission lifecycle and four independent forms, so it exceeds one hour. Adoption-surface verification is included because the pending controls, errors and draft ownership are directly visible to users.

## Tasks

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Define pending submission ownership and repair the Note path | 35m | — |
| [t002](./t002.md) | Apply the contract to Transaction, Balance and Open Account | 25m | t001 |
| [t003](./t003.md) | Verify the user-facing pending and recovery journey | 10m | t002 |
| [t004](./t004.md) | Simplify the changed submission handling | 15m | t003 |
| [t005](./t005.md) | Prove pending draft safety and run dashboard checks | 35m | t003 |
| [t006](./t006.md) | Close out and archive the milestone | 10m | t004, t005 |

## Fresh live reproduction

Production `https://beancount.io`, local main `c5e4cd11a`, QA-owned headless isolated Chromium 155.0.8059.85. Separate fresh owner contexts at 1440×1000 and 390×844, English/light, designated disposable synthetic ledger. Only a real BulkEntries request is held inside its browser and later continued unchanged; no response is substituted.

**Desktop, accepted edits lost on success:**

1. Journal → New Entry → Note. Select existing Assets:Cash and type prefixed text A.
2. Click Create Note Entry and hold its real BulkEntries request. Its single NOTE payload already contains A.
3. The submit button is disabled, but Note content remains enabled and writable, Close is enabled, and the other directive tabs remain enabled. Replace the text with prefixed B; the actual field value and screenshot confirm B was accepted.
4. Release the unchanged request. HTTP 200 reports success. The dialog closes without a decision about B; reopening Note shows an empty field. Independent API readback contains exactly A once, not B.

**Phone, late completion erases a fresh dialog:**

1. Fresh 390px context: submit a different prefixed Note A and hold its one real BulkEntries request. Editing to B is again accepted while pending.
2. Close the pending dialog, reopen New Entry → Note, choose Assets:Cash and type a distinct fresh C. This new dialog is visible, has the exact C value and enabled Create Note Entry. It has not submitted anything.
3. Release the original A request. Its successful completion closes the new C dialog. Reopening Note is empty. Only one BulkEntries request was made in this context; A is booked once and C is absent.

The narrow close explicitly discards B, so loss of B on that close is not claimed. C is a newly opened draft that is removed by an unrelated earlier completion. The two reproductions establish separate consequences of the same missing pending/ownership contract.

**Failure control:** another fresh 390px context holds a prefixed Note request, accepts a newer text value, then aborts that request before transmission. The dialog remains open, shows the classified Connection problem guidance, keeps the latest text and re-enables Create Note Entry. Nothing is booked for this control. Preserve failure recovery while repairing success handling.

## Additional controlled Transaction reproduction

Fresh desktop1440×1000 and narrow390×844 document loads, same production client and designated synthetic ledger, English/light. Before opening the form, intercept every mutation in the owned context; hold each before transmission and ultimately abort it. No mutation reaches the server in these controls.

1. Fill a valid prefixed Transaction with existing Assets:Cash −1.23 USD and Expenses:Food:Groceries +1.23 USD. Let validation and account availability settle; Create Transaction Entry is enabled.
2. Desktop: click Create Transaction Entry. Narrow: use Cmd+Enter from the amount field. Each emits one held BulkEntries request with one TRANSACTION; the submit button becomes disabled.
3. While that request remains held, press Cmd+Enter again from a form input. Each viewport emits a second identical BulkEntries request even though the button is still disabled. This is native Playwright keyboard input in headless Chromium, not a directly dispatched submit event or physical phone keyboard verification.
4. Abort both requests. The actual connection guidance appears; the dialog retains the exact prefixed narration and re-enables submission, with no uncaught page errors. Preserve this recovery.

The directly proven defect is repeated mutation attempts bypassing the pending button lock. Duplicate server bookings are not claimed: all four attempts were stopped before transmission. Independent readback confirms latest ledger commit remains `aa21d26175e523fc6f3d0633ef04acc60ff6773d`, with only original main.bean, unchanged blob/2817 bytes/main-file commit and zero errors.

`transaction-form.tsx:323–329` calls form.handleSubmit(onSubmit) for every Cmd/Ctrl+Enter without a pending guard. Its onSubmit also has no in-flight ownership check. Installed react-hook-form/dist/index.esm.mjs:2164–2218 sets isSubmitting and awaits each supplied callback; it does not reject a concurrent handleSubmit call. Therefore disabling the button alone cannot serialize this path. Make all accepted submit paths share the same in-flight guard, including rapid button/keyboard combinations, and release it correctly on failure. This fits t002's existing duplicate-submission acceptance and t005's real-form tests; no new milestone or API/idempotency project is proposed.

Deployed journal source map again matches transaction-form.tsx SHA-256 `662778881665e21ff435b7ce8215b4c2f5a16c9bc612e40e2a5d11ea5f6abec1`; freshly fetched origin/main has no correction in this path. Evidence: ignored `new-entry-keyboard-pending-submit-control.json` in the existing run directory. Both request gates were released to abort, the temporary context closed, and no fixture or new ledger commit was created. The initial unavailable parent account and a background New Entry link attempted while the URL had already reopened its modal were harness errors excluded before this reproduction.

## Cause and repair boundary

`dashboard/src/features/journal/components/new-directive-dialog/note-form.tsx:97–107` resets the current form and calls onSuccess after an awaited mutation. Only its submit button consumes `formState.isSubmitting` at :200–203; editable fields do not. The shared dialog's `index.tsx:60–67` closes through onOpenChange(false) and broadly clears the cache whenever any child calls success. Its close callback and tab changes have no pending protection or completion ownership.

Transaction, Balance and Open Account use the same reset/success pattern in their own submit handlers. All four pass the same dialog callback; Journal is the dialog's only production renderer. Genuine server writes above used Note; the later controlled Transaction cases prove repeated pending attempts without transmission. Balance, Open Account and other entrypoint links remain source-derived regression scope, not independently reproduced writes.

Make pending input, dismissal/tab changes and success ownership coherent across this shared workflow. A bounded pending lock is a valid solution: do not accept edits the success path cannot retain, and keep an obsolete completion from dismissing a later draft. Preserve the accepted draft and useful retry path on failure. Enforce single-submit protection across button and keyboard paths; retain validation, exact decimal strings, account-availability/auto-open behavior, successful creation, write-outcome warnings and focus return. Avoid a persistent draft store, a global mutation observer or weakening cache/financial-data safeguards. No API, dependency or cross-package change is needed.

Coordinate with w4/238's post-write focus repair without treating focus restoration as draft preservation. w4/241 and w4/247 address distinct file-editor save/create implementations.

## Dedupe and deployed source

All board states searched for New Entry/Note submission timing, pending edits, late success, reset and a newly opened dialog. Completed w3/499 protects balance validation, w3/560 protects account availability, and w3/640 reports writes that leave errors; none owns pending draft lifetime. Current history through `b47c3133d` retains the reset/close pattern. No newer repair or matching pending item was found.

Deployed `ledger._ledgerOwner._ledgerName.journal-DFfgnGSN.js.map` exactly matches all five local sources:

| source under new-directive-dialog | SHA-256 |
| --- | --- |
| index.tsx | `5955e8931d430a5c76e3fb749f202b01f5a0dcfdbe9573030b6b931761978946` |
| note-form.tsx | `66a02b3e69aa929fccc51805c10a2cdd56e4982cc4d9c44af33566a5dc141430` |
| transaction-form.tsx | `662778881665e21ff435b7ce8215b4c2f5a16c9bc612e40e2a5d11ea5f6abec1` |
| balance-form.tsx | `e813defebca410676fbc7e8950f81e0f7a7ab7cd83a9a832f7db41e880335dc9` |
| open-account-form.tsx | `b3a8fa6b8abe9fc2a477c4b2b666f7b0a93242c7b824f88be972094d437663af` |

## Evidence and cleanup

Ignored artifacts in `dashboard/tmp/qa-20261020/dashboard-loop/`: `new-entry-pending-control.json`, visually inspected `note-pending-draft-1440.png` and `note-late-success-fresh-draft-390.png`.

Desktop Note commit `765120fa7`; narrow Note commit `fafce68ac`; exact snapshot restoration `72adcc8c6`. Both genuine writes stored only their original submitted text. Final readback verifies the original main blob `f1a0b83c1aaf9608113c6bd3174bf7d2dab35407`, 2817 bytes and SHA-256 `77c3a591efd311e01d03d2f3a91f2919151c0fb0708e1abe1a10ce6ec7e29915`, one original file, 12 accounts, 29 directives, 16 settled Transaction rows, no QA entries and no ledger errors. All temporary contexts are closed and request gates/interceptors removed.

Other form writes, engines/locales, actual server timeouts, native-toolbar navigation and the repaired implementation remain unverified. No product fix, tests, commit or push was made during this QA filing.

## Definition of done

- [ ] A pending submission cannot silently erase any additional input the UI accepts.
- [ ] Completion of an earlier submission cannot close or reset a later draft.
- [ ] Note, Transaction, Balance and Open Account share the same coherent pending contract.
- [ ] Failure retains accepted text and retryability; success books only the submitted snapshot once.
- [ ] Validation, account/amount contracts, error outcomes and focus remain correct.
- [ ] Meaningful held-request regressions and dashboard gates pass; the completed work is archived through /pm.
