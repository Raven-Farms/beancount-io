# Malformed saved lists can disable two dashboard journeys

Production beancount.io, 2026-10-20 America/Los_Angeles (2026-10-21 UTC), owned isolated headless Chromium155, English/System theme. Local main c6109f667; deployed main-D9qWGMxD.js, full deployment revision unverified. These are deliberately injected browser-cache faults, not evidence that the normal UI produces malformed preferences. No production account, ledger or server preference was changed.

## Journal: Retry and reload retain a non-array filter

Fresh anonymous contexts on public open_ledger/example/journal:

| Viewport | Controlled localStorage value | Settled failure |
| --- | --- | --- |
| 1440×1000 | journal.open_ledger/example.directiveTypes = `{}` | Inline “Something went wrong”, zero tables; TypeError: s.includes is not a function |
| 390×844 | same key = `null` | Same inline boundary, zero tables; TypeError: Cannot read properties of null (reading 'length') |

Try Again repeats each failure, and a full reload still fails. Removing only that key and reloading restores one real Journal table with61 rows including its header, no error alert, and the unrelated local canary still true. The existing records are available; the client preference prevents rendering them. The narrow error screenshot was visually inspected. No empty-data, backend outage or data loss is claimed.

`features/journal/pages/journal-page.tsx:79–98` reads four arrays through useLocalStorageState without a decoder. Its query variables at :186–200 use .length; journal-filters.tsx consumes .includes, .filter and array spreads for directive and subtype selections. `common/hooks/use-local-storage-state.ts:76–85` catches invalid JSON syntax, but a successfully parsed object/null is cast to T without shape validation. The same Journal page also has two boolean display choices; preserve them rather than clearing all Journal state.

Validate these arrays at the feature boundary. Keep known DirectiveType values and valid subtype strings, including legitimate empty-string custom values; do not invent a closed enumeration for free-form custom subtypes. Invalid containers need safe feature defaults, valid empty arrays remain intentional, and valid stored choices must not silently reset. Backend enum inputs must never receive invalid decoded types.

## Changelog: an optional reading list crashes the home page

On the authenticated QA dashboard /ledger, seed only beancount.changelog.readIds with `{}`. A fresh390×844 context settles on the full-page “Something went wrong” screen, title Error, with Go Home/Go Back/Try Again. Details identify TypeError: object is not iterable (cannot read property Symbol(Symbol.iterator)). Try Again and reload repeat it. Remove only readIds and reload: title Dashboard, Dashboard/Activity headings return and the unrelated canary remains true. The root error screenshot was visually inspected.

A separate fresh1440 context starts with valid `[]` and shows Dashboard/Activity. An additional owned same-origin tab sets readIds to `{}`; the real cross-tab storage update changes the already-open dashboard to the same root error, without a reload. This used actual browser storage communication, not a JavaScript-dispatched imitation StorageEvent. Initial quick SSR text before client hydration is excluded; assertions use the settled client state. No release links, social actions or server mutations were invoked.

`common/hooks/use-changelog-watermark.ts:116–120` reads string[] with syncAcrossTabs=true and no decoder; :146 passes it directly to new Set. The hook later spreads the prior readIds when marking a release read. useLocalStorageState's native storage handler at :157–173 likewise publishes any successful JSON.parse result. WhatsNew is its only production consumer, mounted directly under DashboardPage; its failure can replace the entire home page even when no changelog section is visible.

Validate the read-identities list through the existing deserializer for both initial reads and cross-tab updates. Preserve arbitrary valid identity strings and locale-independent release semantics, without requiring every past identity to be in the currently fetched five releases. Invalid updates should leave a safe/last good state rather than throw during render. Preserve the separate valid seenThrough/flaggedFrom watermarks and device-local policy. No new persistent server state or user-facing cache-management flow is needed.

## Dedupe, delivery and cleanup

All board states/tombstones were searched for malformed/corrupted Journal storage, selectedDirectiveTypes, changelog readIds/watermarks and preference decoding. Completed w3/463 scopes Journal keys by ledger; it does not validate their data shape. W4/272 owns the separate BQL history list and can share a bounded decoder, but fixing that consumer alone cannot repair either reproduced page. The four Journal arrays are one consumer group, not one issue per key. Journal metadata/postings booleans and changelog watermark shapes were source-audited compatibility scope, not additional reproduced failures.

Production journal-states-DrHUvehQ.js.map matches current journal-filters.tsx exactly, SHA-256 7422ad37e44ae1814c4bc049fcf8bc6915e5abdaf78ddb4160d6c135c02775e5. ledger.index-Cu6m9-W4.js.map matches use-changelog-watermark.ts exactly, SHA-256 0bb7380d150838727b5cf845bbbd45341484b1ffcf9846b2fceeffa4ad669c14. The Journal page's unchecked consumer block and generic storage helper were source-traced; their complete deployed-file hashes were not established. No current-main shape guard exists in these two consumers through c6109f667.

Ignored evidence in dashboard/tmp/qa-20261020/dashboard-loop/: journal-malformed-cache-control.json, changelog-malformed-cache-fresh-control.json, preference-cache-source-control.json, journal-cache-failure-{1440,390}.png and changelog-cache-failure-390.png. The desktop cross-tab observation is recorded separately in changelog-malformed-cache-cross-tab-observation.json. All owned contexts/tabs closed; the original QA tab, query history and preferences were unchanged. There were no ledger writes or product fixes. Other engines, naturally occurring corrupted profiles and the repaired build remain unverified.
