# w4 · m37 — Resolve README file and image references from their source path

**Worker:** worker1 **Goal:** A rendered ledger README opens its relative file links and displays its relative images from the correct ledger paths. **Status:** done

**Severity:** minor. **Estimate:** 180m across seven tasks, dashboard only.

## Tasks

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./done/t001.md) | Resolve relative file destinations from the README path — **DONE** | 30m | — |
| [t002](./done/t002.md) | Wire contextual native hrefs into rendered READMEs — **DONE** | 25m | t001 |
| [t007](./done/t007.md) | Load relative README images from their authorized file bytes — **DONE** | 55m | t001, t002 |
| [t003](./done/t003.md) | Verify the README-to-file adoption journey — **DONE** | 10m | t002, t007 |
| [t004](./done/t004.md) | Simplify the changed link handling — **DONE** | 10m | t003 |
| [t005](./done/t005.md) | Prove path, image and native-navigation behavior — **DONE** | 40m | t003 |
| [t006](./done/t006.md) | Close out and archive the milestone — **DONE** | 10m | t004, t005 |

## Definition of done

- [x] From a nested rendered README, sibling target.txt and parent ../main.bean open the same existing files as their canonical Files-row links.
- [x] Resolve from the README's ledger path, retaining the current supported main-branch context. Do not reinterpret a filename or parent segment as a directory/branch route.
- [x] The actual DOM href works for keyboard activation and native open-in-new-tab, not only a primary-click callback. Correct encoding, query/fragment and established URL filtering remain intact.
- [x] Root/nested README callers receive consistent context without changing non-README Markdown consumers, authenticated/public access, readable SSR, heading nesting or loading behavior.
- [x] The proved nested relative PNG displays its exact authorized file bytes with the authored alt text, matching the working direct Files preview. Healthy root-relative and absolute image controls still load. Loading, unavailable and denied images retain useful accessible content without hiding the README or leaking another ledger's data.
- [x] Meaningful route/rendered-link/browser checks and dashboard format/lint/test/build pass; record narrow coverage explicitly.
- [x] No fixture residue or unverified production-remediation claim remains. Relative directories, other image formats, raw HTML image attributes and image behavior on other engines remain audit scope unless independently exercised.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. See [live findings](./FINDINGS.md). **A2 — Frictionless onboarding:** a ledger's README should guide a reader to its files and show its diagrams without requiring application-specific absolute URLs in every authored reference. Two actual native file-link activations lose the README folder; ordinary file-row and canonical-link controls open the exact target. A separate nested PNG reproduction at both widths resolves from the Files page instead of the README source and receives HTML; the same file's direct preview and both absolute controls work. Source-context resolution, authorized image-byte rendering and shared-renderer integration with SSR/native-href regressions exceed one hour. Adoption-surface verification is included because README navigation is a user-facing entry path.

## Scope

Repair README-relative file links and the independently proved relative PNG through ReadmeCard's known ledger/path context. Load image bytes through the existing authorized GetLedgerFile capability and preserve alt text; a canonical HTML file-view URL is not an image source. Keep the default AI-message Markdown renderer's existing behavior. Do not add branch support, edit authored README bytes, change access policy, add cross-feature private imports or invent a raw-asset/export endpoint.

## Deployed verification and closeout 2026-10-20

The prior blocker is cleared by actual hosted fixture journeys. At1440×1000 and 390×844, native Enter on nested sibling, parent and main-file references opens the intended canonical file view. Files-row and direct-link controls agree. An encoded space/plus/Unicode filename keeps its query/fragment through navigation; an actual browser modified click opens that same correct URL and exact text in a new tab while the opener stays on the directory. Root Overview README navigation also opens the exact sibling text at both widths.

Nested relative PNGs decode 32×32. Root README and direct Files preview match the full 116-byte fixture SHA-256 8c17c2913093f052a0b7dbcd8b499e7fefe478af687d12d742572600d9c28209; root-relative and absolute 256×256 controls remain correct. A390px viewport has no horizontal overflow. Narrow held-read, modeled FORBIDDEN and genuine missing-file controls retain the authored alt text and README; release of the held real read restores its image. No actual permission policy was changed.

All six new files were removed with two fresh exact ownership/content/metadata checks per deletion: five under a prefixed directory and the initially absent fixed-name root README. No pre-existing file was edited. A concurrent separate QA recheck changed the untouched main file; its 3011-byte version was preserved, not overwritten with this probe's older snapshot. Final verification shows one root file, zero own fixture paths and zero ledger errors; observed own cleanup head 0eefacd09cddb6e3e67de8349ac345d9071c502d. All owned contexts closed and main history/preferences unchanged.

63 focused tests pass at 9975b4b0a, including resolver/native hrefs, image fallback/MIME, SSR/hydration and public loading. Full dashboard format/lint,624 test files (6,585 passed,1 skip) and production build passed at 1cdf076a0 earlier in the same QA pass. Relevant core implementation remains 5ce50fa93. ReadmeCard, resolveReadmeReference and LedgerImage exactly match deployed source; the whole Markdown renderer differs due the separate 282 fragment follow-up, so full deployed revision is unverified. QA changed only board records and disposable hosted fixtures.

Ignored evidence in dashboard/tmp/qa-20261020/dashboard-loop/: readme-deployed-reverify-{snapshot,active,complete}.json, readme-deployed-{source,helper-source}-control.json, readme-deployed-targeted-tests.log and inspected readme-deployed-render-{1440,390}.png. Complete native links, image data, fault labels, creation metadata, deletions and the shared-ledger concurrency observation are retained in the complete record. Initial row-label and root-view timing samples were excluded and replaced with complete controls. See done/t003.md for tested limits. No own hosted fixture residue remains, and the milestone is archived only after the observable DoD holds.

**Related 2026-10-21:** [W4/327](../../327.md) independently reproduces the previously unverified trailing-slash directory branch at both widths: a child-folder href loses the README folder and ./ jumps to the ledger root. Native folder-row and relative-file controls still pass. That new directory repair preserves this completed file/image DoD; all new owned fixtures were removed with a clean ledger.
