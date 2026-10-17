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

- [469 — `bea import --id-key FITID`/`''` silently disables native-ID dedupe](./469.md)
- [470 — `bea import`'s no-importer hint suggests `--account Assets:Checking` and placeholder columns](./470.md)
- [471 — `bea query` text tables print `1.5E+3` and crash on `NaN`/`Infinity`; CSV/JSON answer](./471.md)
- [472 — `bea query --source` dumps a ~200-line traceback for amounts of 10^12 or more](./472.md)
- [473 — `bea list price|commodity -c " HOOL"` validates, then matches nothing with exit 0](./473.md)
- [474 — `bea query PRINT` export drops validity options (`name_*`, tolerance), so it fails `bea check`](./474.md)
- [475 — A stray CR above a managed include makes bea rewrite the wrong line: the user's directive vanishes from load and `price export`](./475.md)
- [476 — An authored price loses to the managed feed after a BOM, or below an ignored line containing `"`](./476.md)
- [477 — Shadowing a feed point with an indented comment leaves orphaned lines: `unexpected INDENT`, `add price` refused](./477.md)
- [478 — `price refresh` accepts an unparseable feed body, replaces the good revision, exits 0](./478.md)
- [479 — `price export` exits 0 with a refused URL include left in the snapshot](./479.md)
- [480 — `MANAGED_PRICE_ORIGINS` entries are not normalized (trailing slash refuses the origin)](./480.md)
- [481 — `engine status` reports an unusable `BEA_ENGINE_PYTHON` override as serving](./481.md)
- [482 — `bea ask` prints a proxy's HTML error page as the message](./482.md)
- [483 — `price export -o a -o b` silently exports to `b`](./483.md)
- [484 — Price-source warnings end in `..`; `upgrade --check` shows raw parser text](./484.md)
- [485 — A repeated global `-f` silently uses the last ledger, so a write lands in the wrong file](./485.md)
- [486 — `add transaction` blames an unclosed `{` on the next posting or the header](./486.md)
- [487 — `add balance --pad-from` on a conflicting same-date assertion gives contradictory, circular advice](./487.md)
- [488 — The w5/363 widen hint drops the booking method and fires for an amount-less leg](./488.md)
- [489 — Futures commodity `/0J` refused as "Division by zero"](./489.md)
- [490 — A no-break space in `add -p` becomes part of the account name; the hint offers to open it](./490.md)
- [491 — `add open -c USD -c ""` silently drops the blank currency](./491.md)
- [492 — `add --into` a new file in a missing directory exits 1 "validation" instead of a usage refusal](./492.md)
- [493 — `bea --json check` answers valid for a ledger `bea check` rejects (extra validations skipped)](./493.md)
- [494 — `doctor linked ROOT file:start:end` no longer resolves include-relative paths (regression from w5/062)](./494.md)
- [495 — An encrypted `.gpg` include breaks `format` and `doctor`; format advises re-saving it as UTF-8](./495.md)
- [496 — Native `check --json` prints `{"errors": []}` or nothing while exiting 1](./496.md)
- [497 — A load-cache path inside an include glob breaks every later command](./497.md)
- [498 — `doctor region --conversion value` rounds the tree, disagreeing with `Net Income`](./498.md)
- [499 — `bea format` refuses a ledger not named `.bean`/`.beancount`](./499.md)
- [500 — `bea check books.bean` never suggests `bea --file books.bean check`](./500.md)
- [501 — `report -a Equity -t 2025` drops previous earnings (clamp runs after the account filter)](./501.md)
- [502 — `report -a "*Food*"` (invalid regex) silently drops `Expenses:FoodTruck`; refusals quote wrapper positions](./502.md)
- [503 — `bea balance -- <term>` forwards dash terms as engine options (`-- -f other.bean` reports another ledger)](./503.md)
- [504 — `report -a` on an account closed before `-t` prints a blank report and `account_filter_empty: false`](./504.md)
- [505 — `balance-sheet -x at_cost` claims a reconciliation with a cross-currency adjustment](./505.md)
- [506 — Zero valuation adjustment and total equity print as "—" under a conversion](./506.md)
- [507 — `list --on-disk` drops real transactions when a plugin shares their location and the header has a quoted comment (regression from w5/401)](./507.md)
- [508 — `add price`/`add balance` advise `--allow-errors` for a syntax error it cannot pass](./508.md)
- [509 — BQL regex functions still read `[[:alpha:]]` as a set and leak a `FutureWarning` (gap in w5/429)](./509.md)
- [510 — "No position matches" names the wrong posting when two share account and units](./510.md)
- [511 — `add balance --amount "… ; note"` silently drops the comment, exit 0](./511.md)
- [512 — `bea format -o a -o b` / `-c 40 -c 70` keep the last value](./512.md)
- [513 — `add balance --pad-from` before the open cites a nonexistent line as an assertion that "already holds"](./513.md)
- [514 — `list` on an included leaf counts the root hint as an error](./514.md)
- [515 — Global `--offline` is ignored by `bea cloud` (and `ask`): `--offline -y cloud ledger delete` deletes](./515.md)
- [516 — `cloud login` with `BEA_TOKEN` set reports success, but the session is never used](./516.md)
- [517 — Gateway timeout (504/524) on cloud writes exits 1 instead of the unknown-outcome exit 4](./517.md)
- [518 — A SOCKS proxy in the environment breaks every cloud command with httpx's pip advice](./518.md)
- [519 — A refused proxy tunnel (407) on cloud writes exits 4 "outcome unknown" (gap in w5/368)](./519.md)
- [520 — `cloud ledger clone --dir` into a non-empty directory asks the server first, then exits 1 (gap in w5/371)](./520.md)
- [521 — `cloud logout` deletes the credential on a malformed `BEA_API_URL` and misclassifies after-send failures](./521.md)
- [522 — A closed pipe on stderr exits 120, and turns a usage exit 2 into 1](./522.md)
- [523 — `format` aborts on a permission-denied include (gap in w5/442)](./523.md)
- [524 — USAGE says `list -a 'Food|Rent'` matches either; `list` filters are substrings](./524.md)
- [525 — Import refusals drop the remembered-settings notes IMPORTING.md promises](./525.md)
- [526 — `list --flag txn` refused, though `add --flag txn` works](./526.md)
- [527 — REFERENCE marks single `--amount` options repeatable and shows `--private` default as True](./527.md)
- [528 — `agent-skills.md` contradicts itself on skill `name` and directory](./528.md)
- [529 — Non-Western 8-bit CSVs are told to use `encoding=cp1252`, which writes mojibake](./529.md)
- [530 — Import skips NFC for importer-extracted accounts and CSV category cells (gap in w3/386)](./530.md)
- [531 — A doubled BOM or zero-width character in a CSV header is invisible and breaks the advised mapping](./531.md)
- [532 — Import preview is not UTF-8 under an 8-bit locale (gap in w5/405)](./532.md)
- [533 — Turkish İ/ı not folded by `list --type` or the CSV column hint](./533.md)
- [534 — Decimal comma in `-p`/balance gives a raw `ValueError`; tag refusal says "letters"](./534.md)
- [535 — `treeify` on non-UTF-8 input gives a raw `UnicodeDecodeError`](./535.md)
- [536 — Only accounts are written NFC despite USAGE; `--into` creates NFD file names](./536.md)
- [537 — `add transactions --partial` is quadratic when a row breaks an existing balance assertion (gap in w5/123)](./537.md)
- [538 — A booking-arithmetic failure aborts a `--partial` batch naming no row; zero-unit total cost gives raw `DivisionByZero`](./538.md)
- [539 — Bulk `amount` shorthand silently overwrites an explicit `cost`/`price`/`price_total`](./539.md)
- [540 — Filtered `list --json` output cannot be re-fed to `add transactions` (`matching_postings`)](./540.md)
- [541 — A `--partial` write drops the NFC/NFD notes of written rows in text mode](./541.md)
- [542 — Cost labels are written with raw control and bidi characters](./542.md)
- [543 — A same-day sale before its purchase is refused despite USAGE's "appearing later in the input"](./543.md)
- [544 — Two `write_directive` calls in one `ask` reply open two approval prompts at once; approving both writes one, and it can hang](./544.md)
- [545 — `ask` REPL sends a quick follow-up question to the proxy twice (stale keep-alive retry)](./545.md)
- [546 — `ask` prints an answer cut off at its own output cap as complete, exit 0](./546.md)
- [547 — `ask` reply cut mid-UTF-8 prints a raw codec error and drops the already-wrote note (gap in w5/373)](./547.md)
- [548 — `ask` answers lose angle-bracket text and HTML blocks](./548.md)
- [549 — `ask`'s BQL tool drops error details and calls an engine crash "Ledger is invalid"](./549.md)
- [550 — `bea ask > out.txt` hides the REPL and approval panel in the file, yet a blind `y` writes](./550.md)
- [551 — Close skill's report step fails on any unpriced commodity (`@`-priced foreign charge, option lot); skills call it an engine failure](./551.md)
- [552 — Ask skill's anomalies/recurring/merchant recipes count postings, not transactions](./552.md)
- [553 — Shared `add open` recipe fails under `nounused`; the documented two-step needs `--allow-errors` the skill forbids](./553.md)
- [554 — Reconcile diagnostic reads refuse on an already-red ledger; no skill allows `--allow-errors` on reads](./554.md)
- [555 — `dedup.md` import-id grammar omits the lot/price `bea` now hashes (sibling of w5/349)](./555.md)
- [556 — Same-day reciprocal prices: reports and `query` value differently and line order decides; `add price` allows it](./556.md)
- [557 — Missing-price summary gives a misleading "no price before DATE" for cash never routed through a cost currency](./557.md)
- [558 — `query` regex pre-check reads `~ '…'` inside comments and string literals, refusing valid queries](./558.md)
- [559 — A stored query whose OPEN date falls on or after its directive date answers `(no rows)` or a bogus CLOSE error (gap in w3/398)](./559.md)
- [560 — `FROM ACCOUNTS`/`FROM Balances` rewritten to a nonexistent quoted table](./560.md)
- [561 — `query -f csv` drops the lot date and label from `position.cost` (gap in w5/465)](./561.md)
- [562 — `ORDER BY price` crashes with `NullType` AttributeError when unpriced postings sort first](./562.md)
- [563 — `SELECT DISTINCT other_accounts` leaks Python syntax text and gives tags/links advice](./563.md)
- [564 — Text `check` exits 0 on a ledger `bean-check` rejects once loads exceed 1 s (helper cache skips validation)](./564.md)
- [565 — `format -i DIR` aborts entirely on one file with `100/0`, naming no file](./565.md)
- [566 — An include cycle gets a "Run with --file <itself>" root hint](./566.md)
- [567 — `doctor missing-open` writes diagnostics to stdout, so `>> main.bean` corrupts the ledger](./567.md)
- [568 — `bea doctor` resolves symlinks in the ledger path: locations under a symlinked directory find nothing](./568.md)
- [569 — `bea doctor` double-counts a file included under two spellings; `roundtrip` crashes (gap in w5/433)](./569.md)
- [570 — `treeify` takes `NYSE:IBM` in a narration as the account column (regression from w5/414)](./570.md)
- [571 — `doctor linked/region` print 26-decimal trees for interpolated legs (regression from w5/101)](./571.md)
- [572 — `doctor roundtrip` in a read-only directory prints a double traceback](./572.md)
- [573 — `bea example` long-span failure gives calendar-year advice the user already followed](./573.md)
- [574 — A write `--into` a file reached under two names validates against a doubled load: wrong assertion written with exit 0](./574.md)
- [575 — Text-mode `query` takes ~2× `--json` on large ledgers (shell kept alive until shutdown)](./575.md)
- [576 — A ledger with a managed price include never uses the load cache](./576.md)
- [577 — `import --apply` validates the same candidate twice (three loads vs one for `add`)](./577.md)
- [578 — A nearby overlay that includes the root takes over write validation and dedupe (regression from w5/343/346)](./578.md)
- [579 — `init` ignores the `$VAR` path refusal (gap in w5/315)](./579.md)
- [580 — `init` through a dangling symlink blames the working directory](./580.md)
- [581 — `--json` `target.file` resolves a symlinked root to a path that loads a different ledger](./581.md)
- [582 — Process substitution for `--rules`/`--config` gives misleading errors (gap in w5/436)](./582.md)
- [583 — With `2>&-`, child processes lack fd 2: errors land in stdout with exit 0, and the query shell loops forever (gap in w5/308)](./583.md)
- [584 — With stdin closed (`<&-`), stdin-reading commands exit 1 with raw `NoneType` attribute errors](./584.md)
- [585 — Ctrl-C in the query shell's `less` pager leaves it running and splitting keystrokes](./585.md)
- [586 — With `TERM` unset, the query shell pages every result, even one row](./586.md)
- [587 — `bea query > out.txt` opens the shell with no visible prompt and writes prompts into the file](./587.md)
- [588 — `bea init` prompts before validating `--date`/`--opening-balance`, then rejects without naming the option](./588.md)

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
