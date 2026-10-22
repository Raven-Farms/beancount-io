# Entry Context accepts uncovered pending edits and lets an obsolete save close another draft

**Major client draft loss · dashboard.** Production https://beancount.io,2026-10-22; owned isolated headless Chromium155.0.8059.85, authenticated QA on its designated synthetic ledger, English/light/UTC. Fresh390×844 and1440×1000 cases independently reproduce both failures. Existing context/source reads are real. Every update is intercepted before transport, then receives a local schema-shaped acknowledgement echoing the submitted entry identity, or is aborted. No hosted source was changed and no actual save/persistence is claimed.

## Pending source edits disappear at acknowledgement

1. Open Journal and activate a source-backed transaction's named Open entry button. Wait for Entry Context, its actual Monaco model and the full real slice to agree.
2. Add a prefixed Beancount comment through native input; verify the full model before Save. Hold UpdateLedgerEntrySourceSlice before transport, checking ledger, entry identity and SHA against the actual context read.
3. Save is disabled, but Editor content still reports aria-readonly=false. Add a second prefixed comment while the request remains held. The exact full model contains the later comment; the one captured request contains only the earlier source snapshot.
4. Release a local successful acknowledgement. Entry Context closes without a Discard your edit? choice at both widths. The accepted later comment has no remaining draft UI.

The390 retained case grows source120→152→187 characters; the independent1440 case105→138→171. These per-context counts reflect separate synthetic transactions, not a claim that the shared QA ledger stayed unchanged between runs. Only prefixed comments are edited locally; no posting/amount change or server loss is inferred.

## An old save closes a different entry's newer draft

1. In additional fresh contexts at both widths, open an entry, add a prefixed source comment and hold its one Save before transport.
2. Activate Close. The existing Discard your edit? choice correctly appears. Explicitly choose Discard; the old entry dialog closes, while its already-started update remains held.
3. Activate another Journal row's Open entry action. Confirm a different entry identity, wait for its actual full source model and add a new prefixed comment. The new source exactly matches that accepted edit and its Save is enabled. Do not submit it.
4. Release only the older entry's locally modeled acknowledgement. The newer dirty Entry Context closes at both widths, with zero discard choices and still only one update request.

The explicit discard consent concerned the old dialog. It did not authorize clearing the subsequently opened different entry's draft. Actual server ordering, stored entry updates, deletion and a physical device remain unverified.

## Working controls

A fresh390 case holds then aborts Save before transport after a later accepted source edit. Entry Context stays open, keeps the exact latest model and enables Save. One native Space activation then emits exactly one retry with that current source; it is also aborted. Close→Keep editing retains the exact draft and the dialog. Preserve these real client failure/dirty controls while protecting acknowledgement and ownership.

Native fixture setup is verified against the entire model. Early unsent cursor/autoindent probes were excluded; one desktop setup context was closed with zero requests. The retained fresh desktop/reopening cases use native Select All→ArrowLeft to add valid comment prefixes, avoiding platform document-end assumptions. The narrow retained case restored its exact original before its first request. No input/model setter or real clipboard is used.

## Cause and bounded repair

entry-context-panel.tsx EntryContextMain keeps isSaving/isDeleting locally. Its Editor onChange at:375 checks only editable, and options at:390 use readOnly:!editable, so the pending state does not protect the source model. handleSave snapshots sourceText and awaits onSave, then updates the old clean baseline. EntryContextPanel's handler at:521–539 awaits the mutation/outcome, clears the cache and calls onSuccess.

entry-context-dialog.tsx at:217–231 keys the panel by ledger/entry, but its completion closure directly invokes onOpenChange(false), without checking whether the originating panel/dialog lifetime is still current. The owning dialog receives dirty reports and confirms user dismissal, but no pending-session ownership. An old panel's awaited callback continues after it has been replaced; its cache refresh and close must not consume a new active draft.

Protect pending source changes and completion ownership together. A real Monaco read-only/change guard plus a bounded pending dismissal policy is sufficient, or use explicit session/snapshot ownership that retains all newer accepted input. If allowing departure while a request is pending, keep subsequent drafts safe through both cache refresh and completion; checking only the final close is insufficient if a refresh still unmounts/reset the current editor. Do not auto-resend, rewrite an in-flight payload, disable guards globally or introduce persistence/API work. Preserve failure recovery, intended dirty discard, source links, stale-SHA/copy behavior, returned-hash navigation and write-outcome reporting.

## Dedupe, callers and source match

All board states searched for EntryContext/UpdateLedgerEntrySourceSlice, pending source saves, uncovered edits and obsolete completion. [W3/565](../../w3/done/565.md) owns intentional dismissal; [251](../done/251.md) follows a successful standalone save's identity; [307](../done/307.md) reports failed stale-draft copying. The different file, New Entry, settings and receipt lifecycles linked in the milestone do not guard this editor/dialog. No newer pending-source/session repair was found in targeted history.

EntryContextDialog's three production callers are JournalPage, Account report and Overview RecentActivityCard; EntryContextPanel is also rendered by standalone EntryPage. Journal is independently exercised here; the other callers, pending deletion, navigation and standalone completion are regression/audit scope.

Observed entry-context-dialog-B2TkwSxx.js.map matches current dialog SHA-256 **fc4b43dfd9c077754ba8c3af9cfa30e75d13fc68ba9a04578eabc2ac956a4f1a**. Served entry-context-panel-BYuf4phL.js.map has full SHA **d80de27d08d4b70d79a3d8bb1bcbc4c8d0e4f9e343ce2d15a0d7bed8cd5bc7cf**; current panel differs after307's copy-feedback work. Its entire EntryContextMain save handler matches current exactly, SHA **cfabdde6ee0167cfae0a468cc41270eab9b79d8f4cf00e73652bb3d8f0040253**, and both served/current editor guards still depend only on permission. The pending defect is not repaired by that separate source change. Full deployed revision remains unverified.

## Evidence and cleanup

Ignored local artifact dashboard/tmp/qa-20261020/dashboard-loop/entry-pending-lifetime-complete-controls.json contains sanitized state/request comparisons. Screenshots entry-pending-source-{390,1440}.png and entry-new-draft-old-save-1440.png; the new-draft screenshot is visually inspected. Five retained contexts plus one excluded unsent desktop setup context closed. Four locally modeled acknowledgements and two aborted update attempts, zero forwarded mutations, route errors or page exceptions. No hosted fixture, cleanup residue, product fix or authored test.
