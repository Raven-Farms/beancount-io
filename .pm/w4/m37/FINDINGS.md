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

Provide contextual relative-file resolution for ReadmeCard and emit correctly encoded native canonical file hrefs. Base sibling/parent normalization on the source README's ledger directory and current supported branch. Preserve root-relative application routes, external/allowed-scheme links, query strings/fragments, existing URL filtering and authored content. Keep fragment-only behavior explicit. Reuse existing registered Files navigation/path conventions; do not merely attach a click handler, infer arbitrary types from filename extensions, or hardcode the synthetic owner/path. Related relative directories/images require careful classification and remain unverified audit scope; do not claim they were reproduced here or add an unrelated asset/API feature.

ReadmeCard has two production callers: directory browsing with a known nested path and Overview's root README. Only the nested directory case was live reproduced. MarkdownRenderer's other production caller is the AI agent message list; changing all Markdown links globally would affect a different context. Keep its default semantics unless separately justified. Retain the ReadmeCard hydration guard, public README loading contract, readable content, headingOffset and access policy. No backend, new dependency or cross-package import is required.

Acceptance includes the exact sibling/parent journeys with real file controls, native href/new-tab behavior, a root README control, encoded filenames and preserved allowed URL forms. Use an actual rendered README and registered route behavior; a resolver-only test or client callback assertion misses native navigation. Run dashboard format/lint/test/build when implementing.

## Dedupe and source proof

All board states/open milestones searched for ReadmeCard, MarkdownRenderer, relative README links and URL bases. Pending w2/m35 covers public README discovery/loading/SEO and its original authored public README has no Markdown links in the recorded performance control. Its ReadmeCard hydration repair c41597059 is present and addresses skeleton/content identity, not link destinations. Completed w4/104 repairs CodeBlock keyboard visibility in rendered Markdown;104 does not own anchors. Completed94 dispatches explicitly typed legacy file URLs to the blob route; it does not infer the intended file behind a malformed relative README URL. Targeted history has no later contextual-link repair. Fetched origin/main changes only unrelated ChangePlan result fields in dashboard; these consumers have no pending local fix awaiting deployment.

Production maps exactly match local sources: readme-card-BjxD4a_m.js.map contains readme-card.tsx SHA-25682aa6fc5583f82c5723731478f402c5c77ecba9e7e265ea985af719eaebeff68; markdown-renderer-0wxzT_cG.js.map contains markdown-renderer.tsx SHA-25698bc6303a54a94dd928cdc39c0926c907a98206317c356addc574281274e2d9e.

## Fixture cleanup and limits

Creation commits: target051c2cd5eb2f7714fb7a37f5949ce49c2394ae11; README45254e2251d3def38e45d3499b24e3963a55ff22. Both files were deleted after exact path/content/blob/creation-commit guards and a second read immediately before each delete. Final cleanup commit51f6371764c3821b562556fca2117f6c43901208.

Verified only original main.bean remains:2817 bytes, blob f1a0b83c1aaf9608113c6bd3174bf7d2dab35407, SHA-25677c3a591efd311e01d03d2f3a91f2919151c0fb0708e1abe1a10ce6ec7e29915, main-file restoration commit7ec77a71a5204f48942418ea9dd4e8c4309a1cad and zero ledger errors. The Git-only fixture directory disappears with its files. All temporary contexts closed; main session preferences/history and OS settings unchanged.

Ignored dashboard/tmp/qa-20261020/dashboard-loop/ evidence: readme-relative-link-roundtrip-control.json, readme-link-active-fixtures.json (original own-fixture metadata/content, now deleted), readme-relative-link-source-maps.json and the inspected narrow screenshot above. No real financial data, email, AI, credential change, product fix, test change, commit or push. Complete narrow recovery/control, root Overview relative links, other URL forms, directory/image links, native toolbar Back and other engines remain unverified.
