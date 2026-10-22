# w6 — Worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty.

## Blocker triage — updated 2026-10-21 UTC

The twenty engine items and Hermes notes039/040 remain blocked; m6 has completed its native/client prerequisites and protected0.3.7 submission, and now waits only for nine accepted versions to become public. Official npm and GitHub release checks at21:08UTC still report WASM0.24.0, last published September 6. On inspected upstream main `51cf2326`, ten engine items have merged source candidates awaiting release; nine notes plus m2 still need contract or semantic changes. No published artifact clears an engine adoption prerequisite. The marketplace run below records prepared packets and two available free submissions. A subsequent task-level pass continues executable validation and client setup inside m6–m10; the blocked labels do not establish that every remaining substep is unavailable. Existing platform, agreement and moderation conditions apply only to the actions that require them.

m6/t001–t012 are complete, including authenticated first queries and default Hermes discovery. All eleven accepted suite 0.3.3 updates are public, all 105 authored files match, and individual installs have been verified in OpenClaw and supported Hermes (init exception retained). Claude Code 2.1.306 resumes real default-model turns at 19:13 UTC, discovers all thirteen skills and scores 113/113 on frozen0.3.6 routing versus102/103 before. The [client release controls](../../docs/skills/client-release-controls-20261021.md) retain two newly found instruction defects and their successful two-client body corrections for candidate 0.3.7. The separately recorded Codex PDF first-open loss leads to measured import/migrate/reconcile repairs. Candidate4 complete Codex cohorts pass115/115 twice but Claude records a new tax-advice/ask miss; candidate5 targets and complete cohorts pass on both clients, with the documented Claude timeout recovery kept separate. Failed cohorts are retained. All six named dependency/adoption prerequisites are now done; protected run39679035375 accepts all nine changed/new versions with successful credential cleanup; current public/host verification follows actual promotion. The [earlier preflight](../../docs/skills/clawhub-release-preflight-20261021.md) remains historical six-release/seven-skip evidence; the combined description repairs make the current anonymous plan nine releases/four unchanged. Hermes's recorded init/source-filter gaps remain separate.

| Items | Verified state | Action that clears the blocker |
| --- | --- | --- |
| [m6](blocked/m6/README.md) | Verified0.3.7 and six named prerequisites done; protected39679035375 accepts nine versions/four skips.00:40UTC public state unchanged. Exact owner reports show nine clean static scans/null primary reports; nine supported scan/writeback jobs accepted202, still queued at01:07UTC, positions2–10/running0. | Continue saved scan IDs without duplicate jobs. ClawHub completes scans/promotes each eligible version; worker verifies its exact public bytes and supported native installs independently. All DoD must hold before closeout. |
| [016](./blocked/016.md), [017](./blocked/017.md), [018](./blocked/018.md), [022](./blocked/022.md), [023](./blocked/023.md), [024](./blocked/024.md), [025](./blocked/025.md) | The seven recorded corrections have merged source candidates retained on inspected upstream main `51cf2326`. No newer supported npm artifact is published. | Rustledger maintainer publishes WASM containing the seven fixes; repository worker adopts one release and runs each note's native and REST/GraphQL/MCP acceptance cases. |
| [029](./blocked/029.md), [034](./blocked/034.md), [037](./blocked/037.md) | [Rustledger PR #2682](https://github.com/rustledger/rustledger/pull/2682) merged 2026-10-19 at 11:03 UTC, covering SUBST, FINDFIRST, and short-circuit guards. | Maintainer publishes a compatible WASM artifact; repository worker adopts it and verifies the exact native/API controls. Merge alone does not clear the release condition. |
| [m2](./blocked/m2/README.md), [026](./blocked/026.md), [027](./blocked/027.md), [028](./blocked/028.md), [031](./blocked/031.md), [032](./blocked/032.md), [033](./blocked/033.md), [035](./blocked/035.md), [036](./blocked/036.md), [038](./blocked/038.md) | Upstream main `51cf2326` retains the missing contracts or affected implementations; no matching correction was identified. Waiting for a release alone is insufficient. | User files or explicitly authorizes the upstream requests below; maintainer implements and publishes; repository worker adopts and verifies. |
| [039](./blocked/039.md) | Latest stable Hermes v0.22.4 (`4d043038`) retains the unchanged scanner. Its fresh 19:24 UTC native init 1.0.2 control still exits 1 with 18 findings/DANGEROUS, without force; [dated evidence](./blocked/039.md#new-stable-release-control--2026-10-21-1924-utc). | Hermes maintainers provide a compatible policy/install path; repository worker installs unchanged init without force and rehearses consent/validation/preservation. |
| [040](./blocked/040.md) | Fresh archive-pinned native controls return fourteen/default and fourteen/all results, including all eleven suite skills; explicit `--source clawhub` returns `[]` with exit 0. Public registry search returns all eleven. | Hermes host/index correction makes both search paths find the suite; repository worker verifies the searches and a returned-listing install without force. |

Release evidence: [npm registry metadata](https://registry.npmjs.org/@rustledger%2fwasm) has 58 versions and only `latest: 0.24.0` (newest publication 2026-09-06), matching [GitHub latest release v0.24.0](https://github.com/rustledger/rustledger/releases/tag/v0.24.0) and the ledger dependency. The January 1.0.0 RC builds are older. Inspected upstream main is [`51cf2326e7d6d61cb4e38dd00b9a0007b9bc851d`](https://github.com/rustledger/rustledger/commit/51cf2326e7d6d61cb4e38dd00b9a0007b9bc851d). This is source/release triage, not a fresh production retest. Every original reproduction and acceptance criterion remains applicable. Per-item source anchors, exact unblock conditions and native host records are retained under `scripts/skills/tmp/w6-audit-20261021/`.

**Rechecked 2026-10-19:** npm WASM latest remains 0.24.0. Rustledger PR #2682 has now merged; the publication prerequisite remains unmet for all twenty engine items. The workflow branch is refreshed on current main and its ten-skill layout; no hosted engine retest or dependency upgrade was performed.

**After PR #181 merged (2026-10-19):** the merge-commit [validation run](https://github.com/bex-co/beancount-io/actions/runs/39341900916) and the [subsequent main run](https://github.com/bex-co/beancount-io/actions/runs/39344911064) both pass; publish is skipped. Created `clawhub-publish` with required reviewer `puncsky` and an exact `main` branch policy, matching the existing MCP registry environment. Read-back confirms no configuration variables or secrets. License approval, publisher handle, naming decision, and token remain outstanding; merge and environment protection are cleared prerequisites. npm WASM and GitHub's latest release still report 0.24.0.

**After PR #182 merged (2026-10-19):** MIT-0 packaging and all eleven licensed bundles are on main at `6d10a07482bf271d596ab8dcf60783cff8f80cc9`. The [main ClawHub run](https://github.com/bex-co/beancount-io/actions/runs/39371492602) passes; publication is skipped. Agent-guidance and secret-scan runs also pass. Environment read-back confirms `CLAWHUB_OWNER=puncsky`, `CLAWHUB_MIT0_APPROVED=true`, and no `CLAWHUB_TOKEN`. The authenticated ClawHub API-token page still shows no tokens; credential creation awaits the existing action-time confirmation. No PR or merge step remains before publication. npm WASM and GitHub's latest release are rechecked and still report 0.24.0; Hermes's latest stable release is still v0.22.2. No engine or host-policy release clears the remaining blockers.

**First ClawHub submission (2026-10-19):** the operator supplied an existing token, now stored on the protected environment. [Run 39372550698](https://github.com/bex-co/beancount-io/actions/runs/39372550698) submits all eleven version 1.0.0 bundles from main `b5f849059` and cleans its credentials successfully. Nine public OpenClaw and eight Hermes installs pass. Options/property remain pending publication; Hermes init remains blocked by host policy. The [registry rehearsal](../../docs/skills/clawhub-rehearsal.md) records those results and the direct published-CLI query control. Agent turns await the operator's choice/configuration of temporary model authentication. No ClawHub credential creation or merge approval is outstanding.

**Options promotion (2026-10-19; by 05:35 UTC on Oct 20):** options becomes public at 1.0.0 and installs in both hosts without force, bringing verified totals to ten OpenClaw/nine Hermes. Only property remains pending publication. [Complete skills CI on `dec916039`](https://github.com/bex-co/beancount-io/actions/runs/39374976210) passes. The upstream npm WASM dist-tag is rechecked and remains 0.24.0, so the twenty engine items remain blocked.

**Publication complete (2026-10-19):** property also becomes public and installs in both hosts, yielding eleven OpenClaw/ten Hermes results. All eleven coexist in one OpenClaw workspace. t007 is closed and archived; t008 retains only Hermes init compatibility and model-authenticated agent queries. No publication or repository merge remains outstanding.

### Upstream requests to get work moving

These are existing blocked findings prepared for an upstream hand-off; no issue, PR, or message was sent. The linked notes contain public synthetic fixtures and contrasting expected/actual results. Deduplicate again before filing.

| Item | Concrete upstream request |
| --- | --- |
| m2 | Expose per-column expression types through WASM `QueryResult`, independent of aliases and available for zero-row/null-first results; preserve String/Decimal/Date distinctions and precision. |
| 026 | Retain authored source maps through WASM `Ledger.fromFiles(...).query(...)` and use the source-aware executor, including included-file posting lines. |
| 027 | Normalize GETPRICE's base/quote arguments as Beanquery does, preserving source commodity data and historical lookup semantics. |
| 028 | Preserve signed SPLITCOMP indices instead of clamping negatives to zero; specify invalid-index behavior explicitly. |
| 031 | Use floor-based fixed-stride DATE_BIN arithmetic before the origin. |
| 032 | Preserve calendar DATE_BIN origin days and month/year boundaries, including short months and leap years; the fixed-day correction alone is insufficient. |
| 033 | Return an Amount in the requested currency for ONLY's zero inventory total; preserve true-null propagation. |
| 035 | Add FILTER_CURRENCY's Position overload and preserve the position's complete cost data. |
| 036 | Match Beanquery BOOL truthiness for strings and tag sets while retaining null propagation. |
| 038 | Preserve integer-only add/subtract/multiply types before type-sensitive operations, with explicit overflow behavior. |

Prioritize the major correctness findings (PRINT/FROM/JOURNAL, authored locations, and quoted-column values), then type provenance and guard/regex compatibility. Coordinate one dependency upgrade for whichever fixes the published artifact actually contains, regenerate the ledger lockfile with Yarn, and verify each finding separately. Source-only fixes, unrelated releases, and adapter query rewrites do not meet the written unblock conditions. Hosted verification follows the normal deployment separately.

## Milestones

- [ ] **m9** — [Reach developer marketplaces and galleries](./blocked/m9/README.md) (10 tasks; A3/A1) ← approved local roadmap, synchronized under `$loopx w6` on 2026-10-21 UTC; **blocked:** payloads prepared; cursor.directory entry in New/native OAuth/query/preview complete; native dedicated-QA journeys, final publisher agreement/operator request and external reviews remain
- [ ] **m10** — [List the connector in independent web directories](./blocked/m10/README.md) (8 tasks; A3/A1) ← approved local roadmap, synchronized under `$loopx w6` on 2026-10-21 UTC; **blocked:** MCPServers.org and MCPMarket free submissions accepted into queues; LobeHub sign-in agreement approval pending

- [ ] **m8** — [Claim and publish the hosted connector on Smithery and Glama](./blocked/m8/README.md) (8 tasks; A3/A1) ← existing local marketplace roadmap, continued under `$loopx w6` on 2026-10-21 UTC; t001 packet shipped; **blocked:** Smithery publisher returns removed-update 403, Glama awaits w2/088 claim and full-day health

- [x] **m7** — [Connect OpenClaw and Hermes Agent to the hosted MCP endpoint](./done/m7/README.md) (9 tasks; A1; backend-v2 fixtures and docs) ← user request 2026-10-16 to list Beancount.io on OpenClaw and Hermes Agent; ADR 019 D8

- [ ] **m6** — [Publish the ledger skills to ClawHub for OpenClaw and Hermes Agent](blocked/m6/README.md) (13 tasks; A3; skills and CI) ← user request 2026-10-16 to list Beancount.io on OpenClaw and Hermes Agent — **blocked:** t001–t012 and six named prerequisites done; 0.3.8 source remediation validated; protected changed-content1.0.4 release and independent eligible public/host checks continue; t013 requires actual DoD

- [x] **m5** — [Include current earnings in balance-sheet equity](./done/m5/README.md) (6 tasks; major; ledger with backend-v2 validation).

- [x] **m4** — [Complete empty-narration transaction lookups across APIs](./done/m4/README.md) (6 tasks; minor; ledger and backend-v2).

- [x] **m3** — [Expose core ledger options consistently across API surfaces](./done/m3/README.md) (7 tasks; minor; backend-v2).

- [ ] **m2** — [Preserve BQL expression types across projection aliases](./blocked/m2/README.md) (7 tasks; minor; ledger with backend-v2 validation) — **blocked:** the engine query result has no column types; needs a published `@rustledger/wasm` release that exposes them

- [x] **m1** — Count canonical BQL rows in MCP text summaries (7 tasks) ← from [003](./done/003.md).

## Inbox

- [041](./blocked/041.md) — MCP.so publication — **blocked:** current $39 mandatory fee needs explicit approval or a documented free route; packet is ready.
- [042](./blocked/042.md) — PulseMCP publication — **blocked:** new listings and changes remain paused; needs supported reopened intake.

- [039](./blocked/039.md) — Recheck Hermes support for consent-gated ledger instruction scaffolding — **blocked:** needs a compatible Hermes host policy; retain the approved workflow and do not force installation.
- [040](./blocked/040.md) — Recheck Hermes source-filtered ClawHub discovery — **blocked:** default search finds all eleven, but `--source clawhub` still returns none; needs a host/catalog correction.



- [016](./blocked/016.md) — Adopt corrected PRINT filtering and cost-preserving rendering (major; ledger; 45–60m after release) — **blocked:** awaiting a published WASM artifact containing upstream 3ad34e07.

- [017](./blocked/017.md) — Adopt upstream BQL date subtraction support (minor; ledger; 35–50m after release) — **blocked:** awaiting a published WASM artifact containing upstream 6972f5ed.

- [018](./blocked/018.md) — Adopt upstream MIN/MAX support for posting amounts (minor; ledger; 35–50m after release) — **blocked:** awaiting a published WASM artifact containing upstream 25fc6be5.



- [022](./blocked/022.md) — Adopt BQL JOURNAL date windows and opening summaries (major; ledger; 45–60m after release) — **blocked:** awaiting a published WASM artifact containing upstream 1324bc25.

- [023](./blocked/023.md) — Adopt correct FROM predicate evaluation in BQL (major; ledger; 45–60m after release) — **blocked:** awaiting a published WASM artifact containing upstream a2d984d6.

- [024](./blocked/024.md) — Adopt hidden ORDER BY keys in subqueries and table groups (minor; ledger; 45–60m after release) — **blocked:** awaiting a published WASM artifact containing upstream 05b8588b.

- [025](./blocked/025.md) — Adopt quoted BQL column resolution (major; ledger; 45–60m after release) — **blocked:** awaiting a published WASM artifact containing upstream 9d3bde86.

- [026](./blocked/026.md) — Restore authored BQL source locations (minor; ledger; 45–60m after upstream support) — **blocked:** needs a published source-aware WASM query binding, not a known local patch.

- [027](./blocked/027.md) — Preserve GETPRICE currency argument normalization (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published Beanquery-compatible WASM lookup.

- [028](./blocked/028.md) — Preserve negative SPLITCOMP component indices (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published signed-index WASM implementation.

- [029](./blocked/029.md) — Preserve Beanquery SUBST replacement and null semantics (minor; ledger; 35–50m after upstream support) — **blocked:** needs a compatible published WASM replacement/null implementation.


- [031](./blocked/031.md) — Adopt floor-based DATE_BIN arithmetic before the origin (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published native fixed-stride correction.

- [032](./blocked/032.md) — Preserve calendar DATE_BIN origins and boundaries (minor; ledger; 45–60m after upstream support) — **blocked:** needs a published native month/year boundary correction.

- [033](./blocked/033.md) — Preserve typed zero amounts from ONLY inventory extraction (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published native zero-preserving extraction.

- [034](./blocked/034.md) — Preserve FINDFIRST prefix and case matching (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published native regex-policy correction.

- [035](./blocked/035.md) — Adopt FILTER_CURRENCY Position overload (minor; ledger; 35–50m after upstream support) — **blocked:** needs a compatible published native overload.

- [036](./blocked/036.md) — Preserve BOOL string and tag-set truthiness in BQL (minor; ledger; 35–50m after upstream support) — **blocked:** needs a published native string/set truthiness correction.

- [037](./blocked/037.md) — Adopt short-circuit BQL logical guards (minor; ledger; 45–60m after upstream support) — **blocked:** needs a published native lazy logical evaluator.

- [038](./blocked/038.md) — Preserve integer arithmetic before type-sensitive BQL operations (minor; ledger; 45–60m after upstream support) — **blocked:** needs a published native integer-preserving arithmetic path.

## Continuation decisions — 2026-10-19

The owner approved applying MIT-0 through `skills/LICENSE` and instructed continued work with routine choices delegated. Verified the already authenticated ClawHub publisher `puncsky`; retained current skill names based on the no-benefit rename evidence; preserved init's intentional ledger-instruction scaffolding. m6/t001 is complete and archived. First publication still needs a ClawHub token and the licensing/package change on main. The current suite has eleven skills including property; packaging and publication preflights use that inventory.

The refreshed eleven-bundle preflight passes ClawHub 0.23.3 dry runs and carries MIT-0 in every output; ten pass Hermes's actual community-source scanner. GitHub environment variables are configured and read back. ClawHub and GitHub both confirm that the publishing token is absent.

## Marketplace execution — 2026-10-21 UTC

| Item | Shipped outcome / evidence | Remaining owner and unblock condition |
| --- | --- | --- |
| m8/t001 | Shared packet implemented in d9c3490f0; metadata/relative links pass; live conformance 10 pass, 0 fail, 6 credential skips. | Done and archived within blocked m8. |
| m8/t002–t008 | Actual signed-in Smithery wizard returns removed-update 403 (6e42b85af); milestone parked in 5d1507e67. No Smithery listing or QA grant. | Smithery/Arcade supported direct intake; publisher plus existing w2/088 Glama claim/private test profile/full-day health. Dependents remain open. |
| m9/t001 | Closed by triage in 0014020d2, already satisfied by packet d9c3490f0. | Done and archived within blocked m9. |
| m9/t002 | Actual Docker registry validator and catalog generator pass; standalone gateway discovery/DCR reaches consent; valid preparation shipped fbe47be0e. Consent canceled from non-QA account; temporary catalog/DCR cleaned, no token. | Dedicated QA browser session/consent, actual gateway query/preview/callback and documented upstream review. |
| m9/t003 | Community listing in New and actual URL-only installation verified; [approved native desktop journey](../../backend-cluster/backend-v2/docs/marketplace-submissions/cursor/native-desktop-rehearsal-20261022.md) completes synthetic-only OAuth,44tools/8resources, Cash49.75USD before/after, one dry-run preview and preview-payee0rows. Grant retained as requested; precise host visibility limits recorded. | Separate official Publisher Terms action-time approval and prepared application submission/receipt, then actual official review/publication verification. Typed community name search now finds the canonical entry; native Cursor QA is cleared; w1/m34/t003 retains VSCode/fallback-port acceptance. |
| m9/t004 | Cline instructions, template/icon and native setup are prepared; exact public catalog feed dedup finds no match, with native rendering limits recorded. Required tested-install confirmations stay unchecked. | Fresh approved Cline QA OAuth/discovery/query/preview, then authorized submission and Cline review. |
| m9/t005 | Concrete GitHub nomination remains unsent. Native VSCode gallery observation is51entries/50names, with its original limits. The separately [completed public API discovery](../../backend-cluster/backend-v2/docs/marketplace-submissions/github/README.md#public-default-gallery-api--2026-10-21-utc), shipped85d46affe, checks both name/identity searches and all560unique records across sixpages with no canonical match. | Authorized operator sends the prepared request; GitHub curation; actual native VSCode QA discovery/install/connection and fallback-port acceptance under w1/m34/t003. The public default-feed read is complete and requires no user-input gate. |
| m9/t006–t010 | Milestone parked 836938677; verification and closing tasks are blocked transitively. | Complete actual eligible publication and native QA prerequisites before closing tasks. |
| m10/t001 | Actual MCPServers.org Free $0 remote submission succeeded; receipt and exact fields shipped 405b2b891. | MCPServers.org review, advertised within two weeks, then public metadata/connection verification. Do not resubmit pending entry. |
| m10/t002 | Actual MCPMarket Free Queue source-repository submission succeeded; receipt/route correction shipped 32fe8a5cb. Remote MCP form costs $69 and was not submitted; no payment. | MCPMarket review, advertised ~4–6 weeks; verify/correct actual hosted endpoint and OAuth metadata after publication. |
| m10/t003 | LobeHub remote manifest and actual CLI auth preflight shipped ffefb6826; supported eligibility established. | Operator action-time Terms/Privacy agreement approval is pending; then user/GitHub connection, repository permission, publication and QA proof. |
| m10/t004–t008 | Deferred transitively; receipts are not public publication or completed closing checks. | Directory moderator publication, LobeHub publisher gate and actual hosted QA verification. |
| 041 | Current MCP.so remote fee remains $39; shared packet ready; no payment/submission. | Owner explicitly approves fee or platform documents a free route. |
| 042 | PulseMCP still pauses new submissions and edits; shared packet ready; no submission. | Platform reopens supported intake/correction route. |

The approved local m8–m10/041/042 drafts were copied into an isolated checkout and shipped; the original dirty drafts remain untouched. All marketplace artifacts/evidence are under `backend-cluster/backend-v2/docs/marketplace-submissions/` and the inventory links from the MCP guide. No repository PR, upstream PR/issue, email, paid placement, new project dependency or ledger modification was made. Temporary third-party validation/runtime dependencies and private login URL logs were removed after use; only public-safe provenance/results remain in package tmp.


**m6 executable again — 2026-10-21:** final0.3.7 native routing and all six named w3 prerequisites are verified and shipped. Protected nine-bundle publication and independent public-byte/host checks proceed from the live milestone; no new user answer is needed.


**m6 submission complete — 2026-10-21:** the execution phase above is followed by successful protected submission39679035375 and an actual public-promotion wait. Continue independent w6 work and every newly public listing; no repeat upload or user resume is needed.
