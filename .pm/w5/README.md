# w5 — General adoption worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty. Existing milestones retain their historical order and source.

## Milestones

- [x] **m1** — Ledger sidebar: richer rows, honest states, post-create landing (9 tasks) ← from /pm-brainstorm 2026-08-17
- [x] **m2** — Accessibility pass on /ledger + gallery (8 tasks) ← from /pm-brainstorm 2026-08-17 — sequenced after m1 (both touch `LedgerItem`)

- [x] **m3** — [Install and verify the eight customer ledger skills](./done/m3/README.md) (8 tasks) ← approved `/pm-brainstorm for w5`; materialized 2026-09-12
- [x] **m4** — [Make real MCP agent journeys reproducible](./done/m4/README.md) (9 tasks) — rescoped 2026-09-15 to the hosted MCP endpoint ← promoted core scope of [w2/009](../w2/blocked/009.md); user routed to w5 on 2026-09-12
- [ ] **m5** — [Verify and complete shipped MCP accounting prompts](./blocked/m5/README.md) (9 tasks) — **blocked:** deploy verified 2026-10-20 (Claude Code 9/9); needs a real bank linked to a QA eval ledger (t004) and the Codex run moved to [w4/232](../w4/232.md) ← approved w5 proposal; reconciled with shipped [w2/008](../w2/done/008.md) on 2026-09-13 — depends on m4 closeout

- [x] **m6** — [Authenticate live prices and report refresh failures](./done/m6/README.md) (7 tasks) ← PRFAQ003 launch gaps; requested 2026-09-21
- [x] **m7** — [Expose live-price provenance in ordinary reports](./done/m7/README.md) (6 tasks) ← PRFAQ003 launch gaps; requested 2026-09-21
- [x] **m8** — [Validate and release authenticated CLI live prices](./done/m8/README.md) (7 tasks) ← PRFAQ003 launch gaps; requested 2026-09-21

- [x] **m9** — [Complete a first month through the installed ledger skills](./done/m9/README.md) (8 tasks, ~5h) ← `/pm-brainstorm for w5`, all three proposals approved with `$pm all for w5` on 2026-09-27

- [x] **m10** — [Migrate an export and continue importing without duplicate transfers](./done/m10/README.md) (9 tasks, ~6h) ← `/pm-brainstorm for w5`, both proposals approved with `$pm for both to w5` on 2026-09-28

- [x] **m11** — [Publish the CLI fixes required by the migration journey](./done/m11/README.md) (8 tasks, ~5h) ← `/pm-brainstorm more for w5`, all three proposals approved with `$pm all for w5` on 2026-09-28

- [x] **m12** — [Graduate a CSV workflow into a tested, maintainable importer](./done/m12/README.md) (9 tasks, ~6h) ← `/pm-brainstorm for w5`, both proposals approved with `$pm for all for w5` on 2026-09-28

- [ ] **m13** — [Install the ledger skills and reach a first query on native Windows](./blocked/m13/README.md) (8 tasks, ~5½h) ← `/pm-brainstorm for w5`, both proposals approved with `$pm for all for w5` on 2026-09-28 — **blocked:** native Windows host access is required

## Dropped

- ~~**032**~~ — Catalog search `private` filter validated but inert — dropped 2026-10-02: the finding reads an include flag as an only filter. The upstream search takes `private` (include private ledgers the caller can see, on by default) and `is_private` (only private ones) as separate parameters, and the three transcripts — `private=true`, `private=false`, no filter — are each consistent with that. Mapping `private` onto `is_private`, or rejecting it, would break a working parameter. Re-file as a documentation note if the two names prove confusing in practice.
- ~~**044**~~ — Mistyped list cursor returns -32603 with a raw Zod dump — dropped 2026-10-02: a numeric `cursor` or a `tools/call` with no `name` is a malformed protocol envelope that no conforming MCP client sends, and the MCP SDK's dispatcher refuses it before any handler of ours runs. Re-coding it means overriding the SDK's own request validation for every list method, for an input only a hand-written probe produces.
- ~~**049**~~ — Responses without `Origin` carry an empty `Access-Control-Allow-Origin` — dropped 2026-10-02: no caller can observe a difference. A request with no `Origin` is not a cross-origin browser request, an empty allow-origin grants nothing, and non-browser clients ignore the header.
- ~~**050**~~ — PUT/PATCH get the router's plain-text 405 — dropped 2026-10-02: PUT and PATCH are not MCP transport methods and no client sends them; the router's standard 405 is already a correct refusal. The in-band, authenticated 405 that ADR007 D9 asks for covers GET and DELETE, the two methods the transport defines.
- ~~**052**~~ — Missing rename source refused BAD_USER_INPUT, not NOT_FOUND — dropped 2026-10-02: the note records the throw as deliberate and offers "or document the category" as a fix. Its sibling for comparison gets NOT_FOUND only by accident of wording (see [036](./done/036.md)), and the one real question — which code a missing file should carry on the edit and rename paths — is already in [051](./done/051.md).
- ~~**466**~~ — SIGTERM/SIGHUP to `treeify`/`doctor`/`example` leaves the upstream child running — dropped 2026-10-15: duplicates open [437](./437.md), which covers the same `capture_native` gap for `example`, `treeify` and doctor captures, plus cloud `git clone` and `upgrade`; the work stays tracked there.

## Inbox

- [872 — Preserve explicitly empty lot labels in transaction tables and query CSV](./872.md) — minor CLI output-fidelity follow-up to 805, 465 and 561; reproduced 2026-10-20.
- [873 — Correct imported-balance padding refusals and their command remedy](./873.md) — minor CLI diagnostic follow-up to 871; reproduced 2026-10-20.
- [874 — Give usable CSV currency advice for an already-open unrestricted account](./874.md) — minor CLI onboarding follow-up to 841; reproduced 2026-10-20.
- [875 — Preserve quotes and backslashes in preset ledger titles](./875.md) — minor CLI title-serialization finding; reproduced 2026-10-20.
- [876 — Retain confirmed zero opening balances in preset creation](./876.md) — minor CLI gap against completed m53's opening-state contract; reproduced 2026-10-20.
- [877 — Match preset creation summaries to actual account counts and opening dates](./877.md) — minor CLI success-output finding; reproduced 2026-10-20.
- [878 — Validate preset currencies before unrelated prompts and retry invalid answers](./878.md) — minor CLI PTY onboarding finding; reproduced 2026-10-20.
- [879 — Refuse portable exports that cannot enumerate required plugin resource directories](./879.md) — minor CLI snapshot-integrity follow-up to 868; reproduced 2026-10-20.
- [880 — Include cached runtime helpers and namespace-package resources in plugin exports](./880.md) — minor CLI dependency-inventory follow-up to 327; reproduced 2026-10-20.
- [881 — Anchor stable import IDs to source transactions across view plugins](./881.md) — major CLI source-identity gap; filtered rows and `currency_accounts` native-ID conflicts reproduced 2026-10-20/21.
- [882 — Pair transfer counterparts one-to-one across ID and date matchers](./882.md) — major CLI duplicate-booking / skipped-deposit follow-up to 821; reproduced 2026-10-20.
- [883 — Render valid account components containing non-ASCII spaces in treeify](./883.md) — minor CLI grammar follow-up to 137; reproduced 2026-10-20.
- [884 — Order same-day bulk trades from bookable lots](./884.md) — minor CLI ordering follow-up to 730 and 543; partial holdings, cost-lot selectors, inferred purchases and short covers reproduced 2026-10-20.
- [885 — Refuse non-regular ingest configs before reading them in AST preflight](./885.md) — minor CLI unattended-hang follow-up to 582 and 851; reproduced 2026-10-20.
- [886 — Merge per-file import sign changes under the memory lock](./886.md) — major CLI opposite-sign booking race after parallel previews; reproduced 2026-10-20.
- [887 — Render control-bearing success paths inertly and keep init hints replayable](./887.md) — minor CLI human-output/path-hint finding; reproduced 2026-10-20.
- [888 — Keep the funded-close guard when check_drained skips a same-day assertion](./888.md) — minor CLI close-policy gap after w2/092; reproduced 2026-10-20.
- [889 — Explain the unavailable prior day for a minimum-date preset opening](./889.md) — minor CLI input-diagnostic finding; reproduced 2026-10-20.
- [890 — Preserve request IDs on Ask HTTP failures](./890.md) — minor CLI error-translation follow-up to 369 and 679; reproduced 2026-10-20.
- [891 — Include BOM-first renamed roots in Ask's model context](./891.md) — trivial CLI context follow-up to 403; reproduced 2026-10-20.
- [892 — Derive Ask query relation labels outside strings and comments](./892.md) — minor CLI tool-annotation follow-up to w3/m51; reproduced 2026-10-20.
- [893 — Avoid opening remembered CSV rules paths that became FIFOs](./893.md) — minor CLI unattended-hang follow-up to 582 and 792; reproduced 2026-10-20.
- [894 — Validate device-login expiry before replacing the stored credential](./894.md) — minor CLI false-success finding; reproduced 2026-10-20.
- [895 — Resolve Debit and Credit decimals independently to preserve withdrawal amounts](./895.md) — major CLI bookkeeping error; reproduced 2026-10-20.
- [896 — Match multi-fill sales to their booked cost lots without importing them twice](./896.md) — major CLI brokerage deduplication gap after 467 and 603; reproduced 2026-10-20.
- [897 — Preserve explicitly selected acquisition dates in import identity](./897.md) — major CLI skipped-sale follow-up to 349; reproduced 2026-10-20.
- [898 — Preserve wide arithmetic totals in `@@` annotations](./898.md) — minor CLI precision follow-up to 059, 802 and 263; reproduced 2026-10-20.
- [899 — Include partial lot constraints in generated import IDs](./899.md) — major CLI skipped-sale follow-up to 349 and 467; label-only and number-only cases reproduced 2026-10-20.
- [900 — Keep payee and narration boundaries in generated import IDs](./900.md) — major CLI skipped-payment follow-up to w1/149 and 140; reproduced 2026-10-20.
- [901 — Preserve exact equity offsets for wide preset opening balances](./901.md) — trivial CLI precision follow-up to 310; reproduced 2026-10-20.
- [902 — Make import price-conflict advice respect `unique_prices`](./902.md) — trivial CLI recovery-advice follow-up to 397; reproduced 2026-10-20.
- [903 — Explain quotes that lose to generated prices](./903.md) — minor CLI price-feedback follow-up to 741; import and included-file add cases reproduced 2026-10-20.
- [904 — Make MCP dry runs refuse what the plan's directive limit will refuse](./904.md) — minor backend-v2 finding from w5/m5/t004; observed 2026-10-21.
- [905 — Scope missing-price route explanations to selected accounts](./905.md) — trivial CLI report-message follow-up to 557 and 748; reproduced 2026-10-20.
- [906 — Infer grouped three-decimal CSV amounts consistently](./906.md) — minor CLI import follow-up to w1/130 and w5/753; space and apostrophe groupings reproduced 2026-10-20.
- [907 — Correct XCD's minor-unit import advice](./907.md) — trivial CLI advisory follow-up to 753; checked against SIX and reproduced 2026-10-21.
- [908 — Keep known zero holding values visible in account trees](./908.md) — trivial CLI report-display follow-up to w3/357 and w1/072; zero-cost and zero-price cases reproduced 2026-10-21.
- [909 — Keep cost lots in the funded-close check](./909.md) — minor CLI closing-guard follow-up to w2/092; offsetting quantities with a residual book balance reproduced 2026-10-21.
- [910 — Check funded children closed by `close_tree`](./910.md) — minor CLI closing-guard follow-up to w2/092; generated descendant closes reproduced 2026-10-21.
- [911 — Honor valid remembered custom date formats](./911.md) — minor CLI import-recall follow-up to w1/m24/t007; unchanged-file refusals and unsafe replacement hints reproduced 2026-10-21.
- [912 — Keep child source accounts in parent-importer identity](./912.md) — major CLI skipped-payment follow-up to 223; separate child-account statements collide despite `--duplicates include`, reproduced 2026-10-21.
- [913 — Warn about native imports closing funded accounts](./913.md) — minor CLI diagnostic follow-up to w2/092; silent closes over 100 USD reproduced in JSON and human output on 2026-10-21.
- [914 — Clarify note/document import lifecycle exceptions](./914.md) — trivial CLI guide follow-up to 351; valid post-close annotations and opening-date controls reproduced 2026-10-21.
- [915 — Preserve empty labels in booked-cost exports and imports](./915.md) — minor CLI printer follow-up to 805; PRINT merges lots and native Cost imports lose the label, reproduced 2026-10-21.
- [916 — Deduplicate imports across metadata and allowed-currency reordering](./916.md) — minor CLI identity follow-up to 224; reordered fields duplicate annotations, and reordered currency lists block repeated openings, reproduced 2026-10-21.
- [917 — Skip unchanged document imports with relative attachment paths](./917.md) — minor CLI reload-identity follow-up to 224; root and included-file imports append the same reference on every run, reproduced 2026-10-21.

The 27 findings from the MCP QA auth sweep against the hosted endpoint (023–054, less the five under [Dropped](#dropped)) were fixed in `backend-cluster/backend-v2` and closed on 2026-10-02 and 2026-10-03; each note under [`done/`](./done/) records what shipped and in which commit. None has been re-observed against the hosted endpoint yet — the fixes reach it with the next backend deploy.

## Blocked inbox

- [431 — `add balance`/`add price`/bare-number adds load the ledger twice for pre-checks](./blocked/431.md) — blocked on a maintainer choice between a pre-commit hook in the shared write validation and plugin-free pre-checks that change refusals.
- [015 — Decide the supported way to give a custom importer a third-party dependency](./blocked/015.md) — blocked on the CLI product owner's choice of the supported environment; the new work does not depend on this decision.

## Execution notes

**Approved sequence:** m12 → m13. m12 completed on 2026-09-29 with both installed-agent journeys on published bea 0.3.1; its guide, independent checkpoints, header repair, and sandbox-cache correction are shipped. m13 is parked until a native Windows host is accessible; all eight tasks depend on that baseline, and live-client acceptance additionally needs both native agents authenticated. Neither milestone changes blocked m5 or 015.

Blocked milestones live under `blocked/` with their reason and unblock condition in a `## Blocked` section; they keep their task IDs and return to `wN/mN/` when work can resume.

As of 2026-09-29, m10, m11, m12 and inbox 019–022 are complete. `beancount-io` 0.3.1 (tag `cli-v0.3.1`) is published to PyPI and Homebrew, and the migration journey passed on it in both clients. m9 and inbox 016–018 are complete. m5 and 015 retain their recorded external unblock conditions. w5 remains a general-purpose adoption queue.

The earlier sequence was m3 → m4 → m5. Real-client MCP journeys run against the hosted endpoint, not a duplicate stack. m3 and m4 have no dependency on each other; m5/t001 depends on m4/t009. The customer skill installation work in m3 builds on w1/m21's completed accounting-engine integration. The larger Plaid sandbox journey remains an explicit deferred follow-up in w2/009. m5 verifies and repairs the four prompts already shipped by w2/008; it does not recreate their registration or bodies.

Authenticated CLI live-price milestones m6 → m7 → m8 completed with CLI 0.3.0 on 2026-09-21. The existing m5 blocker remains independent.
