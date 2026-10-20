# w4 · m37 — Resolve README file and image references from their source path

**Worker:** worker1 **Goal:** A rendered ledger README opens its relative file links and displays its relative images from the correct ledger paths. **Status:** todo

**Severity:** minor. **Estimate:** 180m across seven tasks, dashboard only.

## Tasks

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Resolve relative file destinations from the README path | 30m | — |
| [t002](./t002.md) | Wire contextual native hrefs into rendered READMEs | 25m | t001 |
| [t007](./t007.md) | Load relative README images from their authorized file bytes | 55m | t001, t002 |
| [t003](./t003.md) | Verify the README-to-file adoption journey | 10m | t002, t007 |
| [t004](./t004.md) | Simplify the changed link handling | 10m | t003 |
| [t005](./t005.md) | Prove path, image and native-navigation behavior | 40m | t003 |
| [t006](./t006.md) | Close out and archive the milestone | 10m | t004, t005 |

## Definition of done

- [ ] From a nested rendered README, sibling target.txt and parent ../main.bean open the same existing files as their canonical Files-row links.
- [ ] Resolve from the README's ledger path, retaining the current supported main-branch context. Do not reinterpret a filename or parent segment as a directory/branch route.
- [ ] The actual DOM href works for keyboard activation and native open-in-new-tab, not only a primary-click callback. Correct encoding, query/fragment and established URL filtering remain intact.
- [ ] Root/nested README callers receive consistent context without changing non-README Markdown consumers, authenticated/public access, readable SSR, heading nesting or loading behavior.
- [ ] The proved nested relative PNG displays its exact authorized file bytes with the authored alt text, matching the working direct Files preview. Healthy root-relative and absolute image controls still load. Loading, unavailable and denied images retain useful accessible content without hiding the README or leaking another ledger's data.
- [ ] Meaningful route/rendered-link/browser checks and dashboard format/lint/test/build pass; record narrow coverage explicitly.
- [ ] No fixture residue or unverified production-remediation claim remains. Relative directories, other image formats, raw HTML image attributes and image behavior on other engines remain audit scope unless independently exercised.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. See [live findings](./FINDINGS.md). **A2 — Frictionless onboarding:** a ledger's README should guide a reader to its files and show its diagrams without requiring application-specific absolute URLs in every authored reference. Two actual native file-link activations lose the README folder; ordinary file-row and canonical-link controls open the exact target. A separate nested PNG reproduction at both widths resolves from the Files page instead of the README source and receives HTML; the same file's direct preview and both absolute controls work. Source-context resolution, authorized image-byte rendering and shared-renderer integration with SSR/native-href regressions exceed one hour. Adoption-surface verification is included because README navigation is a user-facing entry path.

## Scope

Repair README-relative file links and the independently proved relative PNG through ReadmeCard's known ledger/path context. Load image bytes through the existing authorized GetLedgerFile capability and preserve alt text; a canonical HTML file-view URL is not an image source. Keep the default AI-message Markdown renderer's existing behavior. Do not add branch support, edit authored README bytes, change access policy, add cross-feature private imports or invent a raw-asset/export endpoint.
