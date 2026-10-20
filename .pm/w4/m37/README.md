# w4 · m37 — Resolve README file links from their source path

**Worker:** worker1 **Goal:** A rendered ledger README opens its relative file links at the correct ledger paths. **Status:** todo

**Severity:** minor. **Estimate:** 115m across six tasks, dashboard only.

## Tasks

| id | title | est | depends_on |
| --- | --- | --- | --- |
| [t001](./t001.md) | Resolve relative file destinations from the README path | 30m | — |
| [t002](./t002.md) | Wire contextual native hrefs into rendered READMEs | 25m | t001 |
| [t003](./t003.md) | Verify the README-to-file adoption journey | 10m | t002 |
| [t004](./t004.md) | Simplify the changed link handling | 10m | t003 |
| [t005](./t005.md) | Prove path and native-navigation behavior | 30m | t003 |
| [t006](./t006.md) | Close out and archive the milestone | 10m | t004, t005 |

## Definition of done

- [ ] From a nested rendered README, sibling target.txt and parent ../main.bean open the same existing files as their canonical Files-row links.
- [ ] Resolve from the README's ledger path, retaining the current supported main-branch context. Do not reinterpret a filename or parent segment as a directory/branch route.
- [ ] The actual DOM href works for keyboard activation and native open-in-new-tab, not only a primary-click callback. Correct encoding, query/fragment and established URL filtering remain intact.
- [ ] Root/nested README callers receive consistent context without changing non-README Markdown consumers, authenticated/public access, readable SSR, heading nesting or loading behavior.
- [ ] Meaningful route/rendered-link/browser checks and dashboard format/lint/test/build pass; record narrow coverage explicitly.
- [ ] No fixture residue or unverified production-remediation claim remains. Relative directory/image behavior is audit scope unless independently exercised.

## Source + Goal linkage

Continuous dashboard QA requested for w4, 2026-10-20. See [live findings](./FINDINGS.md). **A2 — Frictionless onboarding:** a ledger's README should guide a reader to its files without requiring application-specific absolute URLs in every authored link. Two actual native file-link activations lose the README folder; ordinary file-row and canonical-link controls open the exact target. Source-context resolution and shared-renderer integration with SSR/native-href regressions exceed one hour. Adoption-surface verification is included because README navigation is a user-facing entry path.

## Scope

Repair README-relative file links through ReadmeCard's known ledger/path context. Keep the default AI-message Markdown renderer's existing behavior. Do not add branch support, edit authored README bytes or invent an unrelated raw-asset endpoint.
