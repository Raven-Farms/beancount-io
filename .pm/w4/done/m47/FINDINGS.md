# Profile pending submission and draft-lifetime evidence

**Minor · dashboard.** Production https://beancount.io,2026-10-22; owned isolated headless Chromium155.0.8059.85, authenticated QA, English/light/UTC. Fresh390×844 and1440×1000 contexts reproduce each case. All inputs are prefixed synthetic names; real current-profile data stays in memory and is never exported.

## Concurrent ordinary Enter bypasses disabled Save

1. Open /settings/general, wait for hydrated Name → Edit, and fill First Name qa-20261022-pending / Last Name Control.
2. Press native Enter in First Name and hold UpdateProfile before transport. Cancel and updating... Save are disabled, but both name inputs stay enabled.
3. Press Enter in Last Name while the first request is held. A second UpdateProfile starts with the same payload at390.
4. The independent1440 repeat first sends qa-20261022-desktop / Control, then accepts Last Name qa-20261022-newer and Enter. A second concurrent request contains that newer surname while the first still contains Control.

Both requests are aborted before transport. At both widths the dialog remains open, retains the current draft and re-enables Save/Cancel. Native Space on narrow Save then emits exactly one deliberate retry with the retained fields, also aborted. Total five aborted attempts and no actual profile change. This establishes concurrent client requests, not server ordering, duplicate persistence or an observed remote overwrite.

## An older modeled success closes a newly opened draft

1. In separate fresh contexts at both widths, intercept UpdateProfile and hold it locally. GetCurrentUser is an unchanged actual read; retain its selected result in memory only to fulfill the expected response shape.
2. Fill qa-20261022-original-session / Control (desktop uses its own prefixed marker) and activate Save. The single captured input contains those original names.
3. While pending, edit Last Name to qa-20261022-pending-edit. Then dismiss with native Escape at390, independently the actual Close button with Enter at1440. Cancel/Save are disabled, but those dismissal paths work.
4. Activate Name → Edit again and enter a new prefixed first/last-name draft. It is accepted while updating... still shows the original pending request.
5. Fulfill only that original request with a local successful UpdateProfile response, preserving its original submitted names. The newly opened dialog closes immediately at both widths. Reopening has neither new-draft marker; request count remains one.

The old completion consumed the new dialog draft. No server mutation occurred: the success is explicitly a local response model against the deployed client. Ordinary modeled own-session success is a working control: from a settled dialog, Save with qa-20261022-normal-success / Control emits one request and closes its own dialog. Idle Cancel also closes normally. These additional controls total three locally modeled successes across two contexts, with zero forwarded mutations.

## Cause and bounded repair

user-profile-section.tsx handleUpdateName at:129–137 calls updateProfile without an in-flight guard; both input Enter handlers invoke it after their existing isCompositionKey check. Only footer buttons use updatingProfile. The same component's inputs accept pending changes, Dialog at:161 passes onOpenChange directly to setIsNameDialogOpen, and the mutation onCompleted at:98–102 unconditionally closes the dialog and clears both name states. No submission/session ownership relates completion to the currently opened draft.

Guard every submission entrypoint and make pending inputs, dismissal and completion obey one draft lifetime. A bounded pending lock is acceptable; an ownership approach must retain newer accepted input and prevent obsolete completion from closing/resetting another draft. Preserve genuine failed-write draft/error recovery, ordinary idle Cancel/success, exact trimmed values, composition protection, refetch semantics and useful focus. Do not silently queue a second save, apply a late edit to an already sent payload, add a persistent draft store or change API/idempotency behavior. Audit the sibling Username handlers for equivalent protection, without claiming they were live submitted here.

## Dedupe and deployed source

All board states searched for UpdateProfile, UserProfileSection, name/profile pending saves, duplicate submission and obsolete completion. Completed [296](../296.md) repairs composing Enter only. [M33](../m33/README.md) and [M42](../m42/README.md) own different forms; [973](../m48/README.md) is receipt review. No matching settings lifecycle repair was found. GeneralSettingsPage is the sole production caller and /settings/general its route. Targeted history leaves these lifecycle callbacks unchanged after296.

Observed settings.general-CbvDEEZU.js.map contains byte-exact current-main user-profile-section.tsx, SHA-256 **5f6b9df8fe45620f94de861a786d244a7eab7f5da9bc3740db0233efb9dbaab3**. Full deployed revision remains unverified.

## Evidence and limits

Ignored local artifacts: dashboard/tmp/qa-20261020/dashboard-loop/profile-pending-enter-complete-controls.json and profile-pending-lifetime-complete-controls.json; profile-pending-enter-1440.png and profile-new-draft-old-request-1440.png are dialog-only synthetic captures, both visually inspected. Four owned contexts closed. Five attempts aborted before transport plus three locally modeled successful attempts; zero forwarded writes, route errors or page exceptions. No account/ledger mutation, cleanup residue, product fix or authored test. Actual success persistence, refetch failure, username submits, other engines/locales, physical IME and repaired deployment remain unverified.
