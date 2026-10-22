# w4 · m46 — Preserve an unsaved file through ledger refresh

**Worker:** worker1 **Goal:** refreshing a changed ledger cannot silently discard the file currently being edited. **Status:** todo

**Severity:** major client draft loss. **Estimate:** 155m across six tasks, dashboard only. Stored remote content remains correct; no overwritten server data was observed.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Retain the current editor through refresh reads | 35m | — |
| [t002](./t002.md) | Keep a retained draft bound to its original file revision | 35m | t001 |
| [t003](./t003.md) | Verify refresh recovery and adoption guidance | 20m | t002 |
| [t004](./t004.md) | Simplify the bounded editor lifecycle repair | 10m | t003 |
| [t005](./t005.md) | Prove dirty refresh and revision compatibility | 45m | t003 |
| [t006](./t006.md) | Verify repaired journeys and archive the milestone | 10m | t004, t005 |

## Definition of done

- [ ] A dirty existing text file survives native **Out of date — click to refresh** at desktop and narrow widths. Preserve its buffer and editor state, or require an explicit discard decision before replacing it. A successful read alone is never consent to discard.
- [ ] Same-file loading and failed refresh do not destroy the draft. A retained draft stays bound to its original ledger, path and edit-base SHA; fetching a newer remote SHA must not silently grant permission to overwrite that version.
- [ ] Clean view-mode refresh shows the new remote content. Ordinary file/ledger changes, missing/denied files, explicit discard, failed/stale Save, successful-save exit and pending-save keyboard locking retain their intended behavior.
- [ ] Use a bounded current-file lifecycle repair. No global cache-policy change, persistent draft feature, dependency, backend or protocol change.
- [ ] Meaningful integration regressions exercise the real Apollo eviction/refetch and owning editor/router lifecycle. Verify exact retained text, original revision on a prepared save, failure/retry, clean refresh, explicit discard and identity changes. Dashboard format:check, lint, test and build pass.
- [ ] Repeat both-width synthetic journeys, independently verify file contents and cleanup, and record deployed/source status. Archive only when this observable contract holds.

## Source + Goal linkage

- **Source:** continuous dashboard QA,2026-10-21; fresh desktop and narrow reproductions, readbacks, cleanup and source comparison in [FINDINGS.md](./FINDINGS.md).
- **Goal linkage:** **A2 — Frictionless onboarding:** newcomers editing a ledger can refresh collaborator/agent changes without losing their own unsaved work.
- **Expected outcome:** a reader can inspect newer remote changes and either continue the existing draft safely or explicitly discard it, rather than discovering the draft has vanished.
- **Why now:** the named refresh action is available while editing, and its current file-loading branch remounts the sole draft owner. Retention, original-revision compatibility and realistic lifecycle regressions exceed one hour. Adoption review is included because this is a user-facing editing action.

## Scope and dedupe

[W4/241](../done/241.md) repaired pending-save locking and the covered successful-save exit; no save is pending in this finding. [W4/238](../done/238.md) retained the same-ledger layout across metadata refresh, but the file's own loading branch still replaces its editor. Preserve both fixes. [W23/032](../../w23/032.md) owns stale-SHA error classification; retain refusal and draft recovery without duplicating that backend repair. The edit-base SHA requirement here is compatibility for retaining a draft, not a reproduced remote-overwrite claim.
