# w5 — General adoption worker queue (worker1)

**Worker:** worker1 — general-purpose adoption worker; accepts the next highest-impact milestone across packages, topics, and A1/A2/A3 rather than owning a permanent specialty. Existing milestones retain their historical order and source.

## Milestones

- [x] **m1** — Ledger sidebar: richer rows, honest states, post-create landing (9 tasks) ← from /pm-brainstorm 2026-08-17
- [x] **m2** — Accessibility pass on /ledger + gallery (8 tasks) ← from /pm-brainstorm 2026-08-17 — sequenced after m1 (both touch `LedgerItem`)

- [x] **m3** — [Install and verify the eight customer ledger skills](./done/m3/README.md) (8 tasks) ← approved `/pm-brainstorm for w5`; materialized 2026-09-12
- [x] **m4** — [Make real MCP agent journeys reproducible](./done/m4/README.md) (9 tasks) — rescoped 2026-09-15 to the hosted MCP endpoint ← promoted core scope of [w2/009](../w2/blocked/009.md); user routed to w5 on 2026-09-12
- [ ] **m5** — [Verify and complete shipped MCP accounting prompts](./blocked/m5/README.md) (9 tasks) — **blocked:** needs the repairs deployed and a QA ledger with a linked bank ← approved w5 proposal; reconciled with shipped [w2/008](../w2/done/008.md) on 2026-09-13 — depends on m4 closeout

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

- [347 — Leaf hint names the nearest includer, not the root, and looks only two dirs up](./347.md) — CLI QA 2026-10-14
- [348 — `check`/reads on an included leaf give no root hint, only `--allow-errors`](./348.md) — CLI QA 2026-10-14
- [349 — Importer trades with the same shares but a different cost share an import-id; the second is silently skipped](./349.md) — CLI QA 2026-10-14
- [350 — `add balance` in a disallowed currency: dangling upstream message plus useless pad advice](./350.md) — CLI QA 2026-10-14
- [351 — Importer balance/note on an unopened account is counted as ready; `--apply` fails the batch](./351.md) — CLI QA 2026-10-14
- [352 — `treeify` on a missing/dir/unreadable input exits 1 with a class name instead of 2/3](./352.md) — CLI QA 2026-10-14
- [353 — `example -o DIR` advises `--force`, which then refuses the directory](./353.md) — CLI QA 2026-10-14
- [354 — `price status` warning tells the user to run `price status`](./354.md) — CLI QA 2026-10-14
- [355 — `format -i` turns a lone CR inside comments/strings into a line break, breaking or changing the ledger](./355.md) — CLI QA 2026-10-14
- [356 — `beancount-close` flag sweep groups by content, so same-day same-merchant `!` entries count once](./356.md) — CLI QA 2026-10-14
- [357 — Skills still say Beangulp requires libmagic (w5/168 leftover)](./357.md) — CLI QA 2026-10-14
- [358 — ask/close spending recipes sum `cost(position)`, leaving `@`-priced foreign charges unconverted](./358.md) — CLI QA 2026-10-14
- [359 — reconcile skill never negates a liability statement's ending balance; card tie-out is off by twice the balance](./359.md) — CLI QA 2026-10-14
- [360 — reconcile skill takes the last row's balance, wrong for newest-first exports](./360.md) — CLI QA 2026-10-14
- [361 — migrate skill never negates a card's stated balance; derived opening hides it](./361.md) — CLI QA 2026-10-14
- [362 — migrate skill splits a split purchase into per-category transactions; bank import double-books](./362.md) — CLI QA 2026-10-14
- [363 — `init` restricts every category to one currency; foreign charges refused with no remedy](./363.md) — CLI QA 2026-10-14
- [364 — `-x AT_COST`/`UNITS` accepted as a fake currency; `-x cost` suggests `'COST'`](./364.md) — CLI QA 2026-10-14
- [365 — Income-statement series keeps an empty leading interval fragment (`-t 2026-03 -i weekly` opens with a 1-day week)](./365.md) — CLI QA 2026-10-14
- [366 — `cloud status` shows `'dict' object has no attribute 'username'` on a partial profile body](./366.md) — CLI QA 2026-10-14
- [367 — `cloud status` reports a redirect/204 as a rejected credential (exit 3, "log in again")](./367.md) — CLI QA 2026-10-14
- [368 — `cloud ledger create/delete` call a refused connection "outcome unknown" (exit 4)](./368.md) — CLI QA 2026-10-14
- [369 — Text-mode cloud errors drop the backend request ID](./369.md) — CLI QA 2026-10-14
- [370 — Unattended `cloud ledger clone` overrides the user's `core.sshCommand`/`GIT_SSH`](./370.md) — CLI QA 2026-10-14
- [371 — `create --clone` creates the ledger before refusing a non-empty target; remedy drops `--dir`](./371.md) — CLI QA 2026-10-14
- [372 — `cloud ledger clone` without git exits 1 with an Errno instead of the exit-2 precheck](./372.md) — CLI QA 2026-10-14
- [373 — `ask` shows raw `list index out of range`/`Expecting value` on a malformed proxy 200](./373.md) — CLI QA 2026-10-14
- [374 — `ask` approval panel shows tabs as `\x09` but writes realigned spaces](./374.md) — CLI QA 2026-10-14
- [375 — Update check timeout is per-read: trickling index hangs `upgrade --check`, notice costs 3 s every run uncached](./375.md) — CLI QA 2026-10-14
- [376 — `upgrade --check` prints the index's version string unescaped (terminal injection)](./376.md) — CLI QA 2026-10-14
- [377 — Managed price feed accepts `BTC-`/`BTC.` commodities: negative price or broken load, then pinned](./377.md) — CLI QA 2026-10-14
- [378 — Managed-price shadowing misses arithmetic authored prices and matches price text inside strings](./378.md) — CLI QA 2026-10-14
- [379 — `price refresh` failure detail reads "….; serving revision none"](./379.md) — CLI QA 2026-10-14
- [380 — A lone CR in the ledger misclassifies add-time errors (plugin blame, lost prefix, pad refused)](./380.md) — CLI QA 2026-10-14
- [381 — Read commands keep the last of a repeated single-valued option (`-a Food -a Rent` lists Rent)](./381.md) — CLI QA 2026-10-14
- [382 — `--flag ''` writes `*` and `--booking ' '` writes no booking (w5/239 leftover)](./382.md) — CLI QA 2026-10-14
- [383 — Duplicate-entry summary prints `5.0E-7 BTC` (w5/228 leftover)](./383.md) — CLI QA 2026-10-14
- [384 — Bulk `number_total` cost without currency gets the generic "not one token" error](./384.md) — CLI QA 2026-10-14
- [385 — `import --date-format ''` is saved to memory as `""` and breaks the next plain import](./385.md) — CLI QA 2026-10-14
- [386 — Empty `--into ''`/`--rules ''` resolve to the working directory and give directory errors](./386.md) — CLI QA 2026-10-14
- [387 — Path options turn `''` into `.`: `format -i ''` rewrites the cwd, `price export -o ''` writes into it](./387.md) — CLI QA 2026-10-14
- [388 — `treeify --filler ''` crashes with `ZeroDivisionError`](./388.md) — CLI QA 2026-10-14
- [389 — `example -o ''` skips bea's output checks (`forwarded_option` drops `''`)](./389.md) — CLI QA 2026-10-14
- [390 — `example` accepts any date span; year 1 or 9999 runs minutes then fails with a class name](./390.md) — CLI QA 2026-10-14
- [391 — Every ledger write silently splits a hard link to the file (new inode, other name stale)](./391.md) — CLI QA 2026-10-14
- [392 — `bea query` shell history ignores `BEA_CONFIG_DIR`, writes `~/.config/beanquery/history` undocumented](./392.md) — CLI QA 2026-10-14
- [393 — Inactive-account error says "Correct the transaction date" for notes/documents](./393.md) — CLI QA 2026-10-14
- [394 — `add close` before the open or on an unknown account gets bare "Unopened account … is being closed"](./394.md) — CLI QA 2026-10-14
- [395 — "Pad accounts must be active, even with --allow-errors" shown without the flag, repeated](./395.md) — CLI QA 2026-10-14
- [396 — With a pre-existing error, adds are refused as "would leave the ledger invalid" with no `--allow-errors` hint](./396.md) — CLI QA 2026-10-14
- [397 — Under `unique_prices`, `add price` advises `--force`, which can never succeed](./397.md) — CLI QA 2026-10-14
- [398 — `check_commodity` add refusal: bare `<check_commodity>:0`, no label or `add commodity` remedy](./398.md) — CLI QA 2026-10-14
- [399 — `check_drained` close refusal gets statement-assertion advice instead of "drain first"](./399.md) — CLI QA 2026-10-14
- [400 — USAGE's plugin-failure wording differs from output; missing plugin config gets no hint](./400.md) — CLI QA 2026-10-14
- [401 — `--on-disk` keeps a same-date plugin entry stamped with a real line](./401.md) — CLI QA 2026-10-14
- [402 — `add open/close/custom` with a foreign root get bare "Invalid account name" (w5/154 leftover)](./402.md) — CLI QA 2026-10-14
- [403 — `ask` system prompt hard-codes `^Expenses` and never names renamed roots](./403.md) — CLI QA 2026-10-14
- [404 — Non-UTF-8 locale: `treeify`/`doctor` crash with `UnicodeEncodeError`](./404.md) — CLI QA 2026-10-14
- [405 — Non-UTF-8 locale: `list`/`balance`/`--details` write locale bytes plus `İ` escapes](./405.md) — CLI QA 2026-10-14
- [406 — Mixed UTF-8/cp1252 CSV is advised `encoding=cp1252`, which mangles the UTF-8 rows](./406.md) — CLI QA 2026-10-14
- [407 — A failed stdout write exits 120 with "Exception ignored on flushing sys.stdout"](./407.md) — CLI QA 2026-10-14
- [408 — Full disk: every read of a managed-price ledger fails with raw `OSError`](./408.md) — CLI QA 2026-10-14
- [409 — Failed `price export` says "Nothing was written" but leaves a truncated `main.bean`](./409.md) — CLI QA 2026-10-14
- [410 — Full-disk write failures report `OSError: [Errno 27]` as `validation`](./410.md) — CLI QA 2026-10-14
- [411 — Failed load-cache write leaks `WARNING:root:` to stderr](./411.md) — CLI QA 2026-10-14
- [412 — Relative or file-typed `BEA_ENGINE_DIR` accepted unchecked (relative `BEA_CONFIG_DIR` is refused)](./412.md) — CLI QA 2026-10-14
- [413 — Misplaced `-f LEDGER` after `ingest archive` becomes `--overwrite` and replaces filed documents](./413.md) — CLI QA 2026-10-14
- [414 — `treeify` default pattern hard-codes English roots; documented pipeline fails on renamed roots](./414.md) — CLI QA 2026-10-14
- [415 — `example -o FILE --version` writes the version banner as the ledger (with `--force`, over one)](./415.md) — CLI QA 2026-10-14
- [416 — Global options after forwarded commands get no "place it before the command" hint](./416.md) — CLI QA 2026-10-14
- [417 — `check --cache-filename PATH` silently deletes any non-cache file at PATH](./417.md) — CLI QA 2026-10-14
- [418 — `BEANCOUNT_LOAD_CACHE_FILENAME` naming a non-ledger file: every read silently deletes it](./418.md) — CLI QA 2026-10-14
- [419 — Provisioning `rmtree`s an existing non-engine `BEA_ENGINE_DIR` (code-confirmed)](./419.md) — CLI QA 2026-10-14
- [420 — Untagged JSON float metadata is written with binary error (`…890.123` → `…567000`)](./420.md) — CLI QA 2026-10-14
- [421 — Completion: fixed-value options complete as files; fish gets wrapped-help fragments as candidates](./421.md) — CLI QA 2026-10-14
- [422 — `cloud ledger create/delete` call an unreadable 2xx "unexpected response" (exit 1), not unknown outcome](./422.md) — CLI QA 2026-10-14
- [423 — Price-cache blobs from bea 0.3.0/0.3.1 (no digest) are trusted; a truncated one is pinned by 304s](./423.md) — CLI QA 2026-10-14
- [424 — "Pass --debug … for a traceback" shown only for engine-side errors](./424.md) — CLI QA 2026-10-14
- [425 — `add price/commodity -c ''` name internal "Request field 'currency'"](./425.md) — CLI QA 2026-10-14
- [426 — Repeated `sign=` in `--csv` is accepted; the last wins and flips every row's sign](./426.md) — CLI QA 2026-10-14
- [427 — POSIX class in a `--rules` regex leaks `FutureWarning` and matches nothing](./427.md) — CLI QA 2026-10-14
- [428 — A CSV header containing a comma cannot be named in `--csv`](./428.md) — CLI QA 2026-10-14
- [429 — POSIX classes in `query ~`, `report -a`, `treeify -r` silently change meaning and leak `FutureWarning`](./429.md) — CLI QA 2026-10-14
- [430 — `bea check` loads twice: plugin output and side effects happen twice](./430.md) — CLI QA 2026-10-14

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
