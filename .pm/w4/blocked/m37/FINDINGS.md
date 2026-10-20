# Rendered README file links lose their source folder

**Minor, dashboard.** Production https://beancount.io, 2026-10-20, local main c5e4cd11a, deployed main-D9qWGMxD.js; full deployed revision unverified. QA-owned isolated headless Chromium155.0.8059.85, English/light, authenticated owner of the designated disposable synthetic ledger. Complete native navigation/control trace at1440×1000; narrow limitations are explicit below. Setup used the API; tested actions used the real rendered README and Files UI.

## Real fixture and complete desktop reproduction

Create two new prefixed paths only: <fixture-dir>/README.md and <fixture-dir>/target.txt, where fixture-dir is qa-20261020-readme-link-control. The target contains exactly the34-byte text qa-20261020 README sibling target followed by a newline. The README has ordinary Markdown links labelled with the QA prefix:

- sibling: target.txt
- parent: ../main.bean
- direct control: the canonical application file URL for that same target

Open /ledger/<qa-owner>/<synthetic-ledger>/files/tree/main/<fixture-dir>. Both files appear in the directory, and the authored README is rendered below them. Its path is <fixture-dir>/README.md.

1. The ordinary target.txt row has the correct href: /ledger/<qa-owner>/<synthetic-ledger>/files/blob/main/<fixture-dir>/target.txt.
2. The README sibling link's actual raw href remains target.txt. The browser resolves it to /files/tree/main/target.txt, dropping the fixture folder and selecting a directory route. Native Enter reaches that URL, HTTP200, title target.txt · Files, heading Files/target.txt. It does not open the existing sibling file.
3. After a fresh directory reload, the parent link raw href remains ../main.bean. Native Enter reaches /files/tree/main.bean, HTTP200, title/heading Files. The parent segment has climbed into the branch position instead of opening the existing root main.bean file. This is a wrong-destination finding; do not claim either route returns404.
4. Working controls: fresh directory loads followed by native Enter on the actual file row, and separately on the README's explicit canonical direct link, both open /files/blob/main/<fixture-dir>/target.txt. The real read-only Monaco view shows the exact expected text. Thus the target exists and is readable; neither the file's content nor permissions caused the failure.
5. Both relative links are valid file paths when based on the actual README location. Their destination must follow that source-file context, rather than the embedding directory page's browser URL.

The complete desktop trace has zero page errors. One narrow follow-up reached the wrong sibling directory, shown in readme-relative-sibling-wrong-folder-390.png: Files > target.txt with the directory loading skeleton. A later wait in that longer attempt timed out and its complete local result was not retained. A separate fresh narrow retry returned document200 but stayed in directory loading before the README appeared for10 seconds. Those waits are excluded from any complete narrow parent/control or responsive-failure claim. The narrow sibling screenshot was visually inspected; desktop native URLs and file-opening controls are the complete retained proof.

## Cause and bounded repair

common/components/readme-card.tsx receives ledgerId and path, reads the exact README at line27, then passes only content/headingOffset to MarkdownRenderer at line86. The directory caller explicitly passes readmeFile.path at features/ledger-editor/directory-browse/components/ledger-directory-view.tsx:318–322. Thus the consumer already knows the needed source location.

common/components/markdown-renderer.tsx:34–38 renders an anchor with the authored href unchanged. Its props at lines11–16 provide no source-file URL context. Native resolution then uses the embedding Files/tree URL, whose final directory segment also lacks a trailing slash. The same default renderer is appropriate for other contexts, but it cannot resolve a README's ledger-relative file references without the caller's information.

Provide contextual relative-file resolution for ReadmeCard and emit correctly encoded native canonical file hrefs. Base sibling/parent normalization on the source README's ledger directory and current supported branch. Preserve root-relative application routes, external/allowed-scheme links, query strings/fragments, existing URL filtering and authored content. Keep fragment-only behavior explicit. Reuse existing registered Files navigation/path conventions; do not merely attach a click handler, infer arbitrary types from filename extensions, or hardcode the synthetic owner/path. Relative directories remain audit scope; the later independently exercised relative PNG is recorded below. Do not add an unrelated asset/API feature.

ReadmeCard has two production callers: directory browsing with a known nested path and Overview's root README. Only the nested directory case was live reproduced. MarkdownRenderer's other production caller is the AI agent message list; changing all Markdown links globally would affect a different context. Keep its default semantics unless separately justified. Retain the ReadmeCard hydration guard, public README loading contract, readable content, headingOffset and access policy. No backend, new dependency or cross-package import is required.

Acceptance includes the exact sibling/parent journeys with real file controls, native href/new-tab behavior, a root README control, encoded filenames and preserved allowed URL forms. Use an actual rendered README and registered route behavior; a resolver-only test or client callback assertion misses native navigation. Run dashboard format/lint/test/build when implementing.

## Dedupe and source proof

All board states/open milestones searched for ReadmeCard, MarkdownRenderer, relative README links and URL bases. Pending w2/m35 covers public README discovery/loading/SEO and its original authored public README has no Markdown links in the recorded performance control. Its ReadmeCard hydration repair c41597059 is present and addresses skeleton/content identity, not link destinations. Completed w4/104 repairs CodeBlock keyboard visibility in rendered Markdown;104 does not own anchors. Completed94 dispatches explicitly typed legacy file URLs to the blob route; it does not infer the intended file behind a malformed relative README URL. Targeted history has no later contextual-link repair. Fetched origin/main changes only unrelated ChangePlan result fields in dashboard; these consumers have no pending local fix awaiting deployment.

Production maps exactly match local sources: readme-card-BjxD4a_m.js.map contains readme-card.tsx SHA-25682aa6fc5583f82c5723731478f402c5c77ecba9e7e265ea985af719eaebeff68; markdown-renderer-0wxzT_cG.js.map contains markdown-renderer.tsx SHA-25698bc6303a54a94dd928cdc39c0926c907a98206317c356addc574281274e2d9e.

## Fixture cleanup and limits

Creation commits: target051c2cd5eb2f7714fb7a37f5949ce49c2394ae11; README45254e2251d3def38e45d3499b24e3963a55ff22. Both files were deleted after exact path/content/blob/creation-commit guards and a second read immediately before each delete. Final cleanup commit51f6371764c3821b562556fca2117f6c43901208.

Verified only original main.bean remains:2817 bytes, blob f1a0b83c1aaf9608113c6bd3174bf7d2dab35407, SHA-25677c3a591efd311e01d03d2f3a91f2919151c0fb0708e1abe1a10ce6ec7e29915, main-file restoration commit7ec77a71a5204f48942418ea9dd4e8c4309a1cad and zero ledger errors. The Git-only fixture directory disappears with its files. All temporary contexts closed; main session preferences/history and OS settings unchanged.

Ignored dashboard/tmp/qa-20261020/dashboard-loop/ evidence: readme-relative-link-roundtrip-control.json, readme-link-active-fixtures.json (original own-fixture metadata/content, now deleted), readme-relative-link-source-maps.json and the inspected narrow screenshot above. No real financial data, email, AI, credential change, product fix, test change, commit or push was involved in that initial phase. Complete narrow file-link recovery/control, root Overview relative links, other URL forms, directory links, native toolbar Back and other engines remain unverified. The relative-image check below is independent and includes both widths.

## Post-filing relative PNG reproduction

Production, local main `38a758352`, same owned headless Chromium, English, fresh authenticated cookie-only contexts at1440×1000 and390×844. Create only `qa-20261020-readme-image/README.md` and `qa-20261020-readme-image/pixel.png` in the designated disposable ledger. The PNG is a generated32×32 green square,116 bytes, SHA-256 `8c17c2913093f052a0b7dbcd8b499e7fefe478af687d12d742572600d9c28209`. The README contains:

```markdown
# qa-20261020 README image controls

![qa-20261020 relative image](./pixel.png)

![qa-20261020 root-relative control](/lgasset/logo.png)

![qa-20261020 absolute control](https://beancount.io/lgasset/logo.png)
```

Open `/ledger/<qa-owner>/<synthetic-ledger>/files/tree/main/qa-20261020-readme-image`. At both widths, the relative img retains raw src `./pixel.png` and requests `/files/tree/main/pixel.png`, dropping the README directory. The real response is HTTP200 `text/html; charset=utf-8`, not image bytes. In a settled sample the native img is complete with naturalWidth0 and `decode()` rejects with EncodingError. The visible broken-image icon/alt text is captured and the narrow crop was inspected. An initial desktop sample still waiting for decoding was retained only as timing context; the separately settled result proves the failure.

Both root-relative and absolute controls receive HTTP200 image/png and decode at256×256. Native Enter on the ordinary pixel.png file-row link opens the correct canonical blob route; the existing ImageFileView decodes the same uploaded PNG at32×32 with its current data:image/png source. These direct-file controls pass independently at both widths. No page errors or horizontal overflow occurred, and no image request/API response was fabricated.

ReadmeCard still supplies only content/headingOffset to MarkdownRenderer, and the renderer has no contextual image override. Default img resolution therefore uses the embedding Files page URL rather than the known README path. Unlike the existing anchor repair, an image also needs actual bytes: a canonical Files/blob route returns an HTML viewer and is not a correct img src. Extend the same source-context milestone with existing authorized GetLedgerFile reads and correctly typed image-byte rendering, retaining alt text and honest asynchronous failure content. Preserve existing access rules and absolute controls, keep non-README/AI-message behavior unchanged, and do not add a raw-asset/export endpoint, dependency or feature-private cross-package import. Root Overview images, directories, other formats and raw HTML image attributes remain audit scope. A fresh refetch of both production source maps again exactly matches the two hashes above; source history/all-board searches found no separate relative-image repair.

Image creation commit `09c495fa70ed4026180453da4dd067c56e7e411d`; README creation `1c16ae23f4ce7a14193686902be5e2dbf860084f`. Both were deleted after two fresh exact path/content/blob/size/creation-commit reads; final ledger cleanup commit `6785a04934ea89f763773e83555a4e3c54f1903e`. Final verification contains only main.bean,2817 bytes and blob `f1a0b83c1aaf9608113c6bd3174bf7d2dab35407`, with byte-exact original content and zero ledger errors; its returned final last-commit metadata is `0eee319a63df5268e55d9241111f89669911c4f8`. The original main bytes were never edited by this fixture setup. The first final read mistakenly requested a nonexistent commit-query field after the deletes had already succeeded; it was excluded as a harness/schema error, and the corrected genuine file/directory/error verification passed. Both temporary contexts are closed. The milestone now has seven tasks/180m, including an image integration task before the closing tasks.

Evidence in the same ignored dashboard directory: `readme-image-seed-control.json`, `readme-image-ui-1440.json`, `readme-image-complete-control.json`, `readme-image-fixture.png`, and the inspected `readme-relative-image-settled-390.png`. The complete record contains settled desktop/narrow image states and working direct previews. Other engines, physical devices, denied/missing image reads and the repaired build remain unverified. No product fix was implemented.
