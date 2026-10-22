# Failed recording drops the reviewed receipt and Try Again starts over

**Minor · dashboard.** Production https://beancount.io,2026-10-22; owned isolated headless Chromium155.0.8059.85, designated synthetic QA ledger, English/light/UTC. Fresh390×844 and1440×1000 repeat the same network-failure path. Upload URL/PUT and parsed receipt responses are local fixtures; the Record request is aborted before transport. A separate1440 context exercises a local success:false envelope. No real upload, parsing/AI request or receipt write occurs.

## Reproduction

1. Open /ledger/<qa-owner>/<synthetic-ledger>/receipt and select the prefixed local PNG. A local parsed response supplies2026-08-01, original prefixed payee/description and12.50USD with Checking/Coffee accounts.
2. Correct Payee and Description to new prefixed review markers and Amount to18.75. The preview and captured InsertReceiptTransaction contain these exact corrections and18.75/-18.75USD postings.
3. Abort only that insert before transport. Both widths replace the entire review with Something went wrong / Connection problem / Try Again. There are zero review inputs; the parsed/uploaded receipt and corrected fields have no remaining review UI.
4. Activate Try Again (pointer at390, native Enter in the separate1440 refusal case). The workflow shows Drag and drop your receipt here / Choose File, with an empty file input, zero review inputs and no retained corrections. No second insert starts.
5. The independent1440 local success:false result instead shows Failed to record receipt transaction, then reaches the same empty upload state on Try Again. The fresh1440 network-abort repeat confirms the primary failure is not specific to that modeled false branch.

Expected: recording failure preserves the already reviewed data and uploaded reference so the reader can inspect/correct it and deliberately retry recording. The existing action labeled Try Again must not silently require starting extraction and review again. Actual: both the error transition and its reset action discard all review state. This does not establish a server failure or actual failed booking; the write never reached the server.

## Controls and cause

A fourth fresh390 context corrects a review field and explicitly activates Upload Different Receipt. It intentionally returns to the empty uploader and starts no insert. Preserve that deliberate reset behavior. Original [pending-success controls](./source-973.md) independently show ordinary pre-submit corrections serialize exactly and modeled success displays its submitted snapshot.

use-receipt-workflow.ts models error only as {step:error,message}; both submit refusal and catch replace submitting's objectKey/parsed state with that context-free error. receipt-page.tsx mounts ReceiptReviewForm only during review/submitting, so either error unmounts its local react-hook-form values. The shared error view's Try Again calls workflow.reset, which sets idle. Its upload/parse failure handling is reused for recording failure even though the latter has an existing corrected review to retain.

Keep recording failure in a review-capable state or an equivalent bounded lifecycle that preserves exact form values, parsed/upload context and the existing objectKey. Surface a useful error and deliberate retry without automatic resubmission or repeated upload/AI parsing. Retain the honest outcome of ambiguous transport errors; preservation alone must not claim an unconfirmed booking is absent. Preserve exact decimal strings, civil dates, accounts/currency/document selection, explicit reset and initial upload/parse failure behavior. No backend/API change is needed.

## Dedupe and source match

All board states searched for receipt failure/retry, ReceiptReviewForm/useReceiptWorkflow and review draft recovery. Original973 explicitly left failure recovery unverified; this new evidence expands that same standalone review lifecycle. CSV Import's explicit Start Over policy in completed280 is not this Try Again action. Mobile capture/retry and backend atomic insertion findings own different implementations. No newer receipt workflow repair appears in targeted history.

The same observed receipt-PtmQUK7G.js.map matches current-main workflow SHA-256 **d2732e910f286f2e7e624abfe5c07b7e8d9c32d96f74c043176e033a88669697**, review **3fc8a260c8fa0f9f62181cf90d8a16f9f8adf4b9c12121cb3bde8efad796c303**, and page **cb9ce9e67d41b51cbaed41d8c696cdacde156cde8906e68bde4f48d9c9c2ec3e** recorded in the original controls. Full deployed revision remains unverified.

## Evidence and cleanup

Ignored local artifacts: dashboard/tmp/qa-20261020/dashboard-loop/receipt-failure-recovery-complete-controls.json, prefixed PNG, and receipt-record-refusal-1440.png (visually inspected). Four fresh contexts closed for this failure/control sequence: two inserts aborted before transport, one local refusal and one explicit reset with no insert. The earlier pending-success sequence closed three contexts and locally modeled three successes. Zero hosted writes, real upload/AI calls, route errors or page exceptions; no hosted cleanup residue, product fix or authored tests.

Actual refusal/persistence, uploaded-reference expiry, manual retry after repaired retention, pending navigation/reload, other engines/locales and repaired deployment remain unverified.
