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

- [630 — Entry metadata `filename:`/`lineno:` makes a written entry look plugin-made: hidden from `--on-disk`, re-imported as new, `list` crash](./630.md)
- [631 — `list --search` cannot find a multi-line narration by the text the table shows](./631.md)
- [632 — Hosted ledger: shadowing a feed point with an indented comment leaves orphaned lines (follow-up of w5/477)](./632.md)
- [633 — Trivial follow-ups to w5/475, 479, 480: "disabled" for ignored origins, stale `--allow-errors` help, BOM option location](./633.md)
- [634 — An importer config calling `sys.exit` is reported as "engine did not answer" and, with `--apply`, exit 4 "outcome unknown"](./634.md)
- [635 — `ingest extract -o` on a module binding `CONFIG` by import exits 0 and writes nothing (gap in w5/167)](./635.md)
- [636 — A blocked import row's "opens after this row" names a vanished staging file](./636.md)
- [637 — Importer rows with unopenable account names or bad currencies get remedies `bea add` refuses (gap in w3/386)](./637.md)
- [638 — Importer row failures are not attributed to rows (unbalanced row "ready", "Directive 2 of 3", bare type errors)](./638.md)
- [639 — Importer-shape refusals name neither the importer nor the fix (legacy entry, class entry, single directive)](./639.md)
- [640 — A price refresh deletes the effective file a concurrent load is reading; racing fetches leave orphan revisions](./640.md)
- [641 — With the cached price blob missing or corrupt, a failing fetch never backs off](./641.md)
- [642 — Managed sources are fetched one after another: 5 s per slow source per command](./642.md)
- [643 — `--strict-prices doctor roundtrip` prints a 184-line traceback (sibling of w5/572)](./643.md)
- [644 — Strict/unavailable price messages give the wrong cause (future stamp, no stamp, no cache)](./644.md)
- [645 — Price cache/URL edge cases: future `next_refresh_at`, dot-segment aliases, ETag `"head"`](./645.md)
- [646 — TAB after two different `-f` values prints an 11 MB traceback instead of completions (regression from w5/485)](./646.md)
- [647 — `engine status` calls an override usable when it has no `bean-check` beside it (incomplete fix of w5/481)](./647.md)
- [648 — `upgrade --check` still accepts null/empty versions and Homebrew HTML with exit 0 (incomplete fix of w5/484)](./648.md)
- [649 — A BOM-prefixed HTML error page still reaches `bea ask` (incomplete fix of w5/482)](./649.md)
- [650 — A non-UTF-8 byte in an `add` argument gives a raw `UnicodeEncodeError`](./650.md)
- [651 — With an included leaf (or stdin) as input, `-o` can replace the root ledger or join its include glob, exit 0 (gap in w5/072)](./651.md)
- [652 — `price export` maps an external include and an in-tree `_shared/01-x.bean` to one destination; snapshot fails `check`, exit 0](./652.md)
- [653 — `add document --into` a symlinked include refuses a valid receipt (path judged at the link target)](./653.md)
- [654 — Cwd-relative `--into` from a subdirectory gets advice to create a new include instead of the root-relative rule](./654.md)
- [655 — Reads of a ledger with a local plugin leave `__pycache__` beside the ledger](./655.md)
- [656 — `-p "Assets:Cash 10/0-5 USD"` leaks `SystemError` instead of the zero-divisor refusal (regression from w5/489)](./656.md)
- [657 — A zero-width space in `add -p` still yields an invisible duplicate account via the printed `add open` (incomplete fix of w5/490)](./657.md)
- [658 — An earlier-dated duplicate `add open` hint names the unwritten proposal line (incomplete fix of w5/488)](./658.md)
- [659 — A validating `add balance --pad-from` skips the same-day conflict and duplicate checks (incomplete fix of w5/487)](./659.md)
- [660 — Trivial gaps in w5/487/488/490: `--force` hint loop, wrong filled-in leg, NBSP in `--amount`](./660.md)
- [661 — `add` exits 0 on a ledger `check` rejects for data-type errors (gap next to w5/493)](./661.md)
- [662 — On a forecast ledger, `import --duplicates skip` drops the real payment on the template date (sibling of w5/325)](./662.md)
- [663 — Under check_commodity with `--allow-errors`, the refusal blames the pre-existing currency, not the new one](./663.md)
- [664 — Under nounused/pedantic, plain `add balance` cannot be a staged account's first use outside a terminal (gap in w5/221)](./664.md)
- [665 — implicit_prices + unique_prices: a second same-day FX trade gets a bare `Disagreeing price entries` (incomplete fix of w5/397)](./665.md)
- [666 — Plugin-triggered write refusals unattributed or misattributed (leafonly, coherent_cost, close_tree, auto_accounts)](./666.md)
- [667 — A plugin error with `source=None` makes every write crash with an AttributeError](./667.md)
- [668 — A whole-number ledger with one `@@` total prints every figure with 25 decimals](./668.md)
- [669 — `--meta` writes a wide negative number rounded (sibling of w5/263)](./669.md)
- [670 — `BEANCOUNT_LOAD_CACHE_FILENAME=main.bean bea query --source main.bean` deletes the root ledger, exit 0 (incomplete fix of w5/497)](./670.md)
- [671 — Large encrypted includes still trip doctor and native `check` text scans; globs inside them escape the guards (incomplete fix of w5/495)](./671.md)
- [672 — Native `check --json` prints nothing for duplicate or unreadable includes (incomplete fix of w5/496)](./672.md)
- [673 — An unreadable `--into`/`--rules`/`-o` dir is reported as "engine did not answer" and exit 4 "outcome unknown" (gap in w5/120)](./673.md)
- [674 — A plugin calling `sys.exit` leaks its status: exit 2/7, exit 4 on writes, silent exit 0](./674.md)
- [675 — `query --source`, the shell and doctor compat skip the `BEA_ENGINE_PYTHON` check (gap in w5/309)](./675.md)
- [676 — `init`/`price export` report an engine killed after writing as "produced no result" (exit 1, not 4)](./676.md)
- [677 — The same conflicting same-day price exits 2 from `add price` but 4 from `import --apply`](./677.md)
- [678 — `format FILE` / `-o` on an unparseable file exit 0 echoing it unchanged](./678.md)
- [679 — `bea ask` answered with a redirect says "Could not reach the server"](./679.md)
- [680 — Small exit-contract slips: wrong blame, `exit -11`, group-without-subcommand JSON, `--limit 0`, `price status` JSON](./680.md)
- [681 — `list --on-disk` drops a real document (cwd-dependent) or a `pushtag` note when a plugin copies it (incomplete fix of w5/507)](./681.md)
- [682 — `add price`/`add balance` still advise `--allow-errors` for an unopened pad account (incomplete fix of w5/508)](./682.md)
- [683 — BQL patterns built with `&&`/`||`/`~~` at run time exit 0 with a raw FutureWarning (incomplete fix of w5/509)](./683.md)
- [684 — `bea import` on a ledger with a syntax error still offers `--allow-errors` (gap in w5/508)](./684.md)
- [685 — `PRINT -f beancount` export fails `check` when an include uses default roots (incomplete fix of w5/474)](./685.md)
- [686 — `--json format` skips an encrypted include without naming it (incomplete fix of w5/495)](./686.md)
- [687 — Five doc sentences describe behavior today's fixes changed](./687.md)
- [688 — An explicit `--pad-date` before the open now gets a looping "date the balance after the open" hint (regression from w5/513)](./688.md)
- [689 — `--offline` still allows forwarded `bea price`, `engine enable` and a `-h`-valued cloud create (incomplete fix of w5/515)](./689.md)
- [690 — Logout treats 504/524 as a plain failure; 521–523 are wrongly reported as "the request arrived" (incomplete fix of w5/517)](./690.md)
- [691 — init's "Record purchases" line runs against no ledger for a non-default file name](./691.md)
- [692 — Import before init's date blocks one account at a time; remedy skips the opening balance](./692.md)
- [693 — init --currency X_ passes init's check, then fails with Invalid token](./693.md)
- [694 — bea --file DIR init exits 4 "never overwrites" for an empty directory](./694.md)
- [695 — A ~name path with no such user exits 1 "Could not determine home directory"](./695.md)
- [696 — A 0-ready import preview still says "repeat with --apply"](./696.md)
- [697 — Zero-sum opening balances write Equity:OpeningBalances -0 USD (regression from w5/310)](./697.md)
- [698 — Three slips in USAGE "Creating a ledger"](./698.md)
- [699 — Other SOCKS spellings and unknown proxy schemes still fail as unexpected; refusal names the wrong variable (incomplete fix of w5/518)](./699.md)
- [700 — An IDNA-invalid BEA_API_URL passes the URL check; logout deletes the credential without sending anything](./700.md)
- [701 — Logout drops the request ID on a lost or unreadable answer; USAGE still gives the old exit codes (gap in w5/521)](./701.md)
- [702 — A proxy that drops the CONNECT makes cloud writes and logout exit 4 "outcome unknown" (gap in w5/519)](./702.md)
- [703 — A malformed BEA_TOKEN is told to run cloud login; logout exits 3 instead of the BEA_TOKEN no-op](./703.md)
- [704 — ingest extract -e misses duplicates in a BOM or NFD ledger, with no warning](./704.md)
- [705 — treeify treats - as a file name: -o - writes ./-, and treeify - reads it instead of stdin](./705.md)
- [706 — ingest extract: -e DIR ends in a traceback; -o into a read-only directory exits 1 after running, not 3](./706.md)
- [707 — Three paths still miss w5/522's pipe statuses: --json --allow-errors exits 1, bare bea 120, native failures 141](./707.md)
- [708 — An include glob through an unlistable directory silently drops its files; check exits 0](./708.md)
- [709 — A mode-000 include named by two roots is reported for the first includer only](./709.md)
- [710 — A BOM on line 1 hides a first-line pushtag/pushmeta and option name_* from the write checks](./710.md)
- [711 — A file ending inside an unterminated string makes add blame the new entry, not the broken line](./711.md)
- [712 — A lone CR as the last byte does not converge under format -i](./712.md)
- [713 — Code-page check misses Czech, Turkish and Shift-JIS, skips remembered cp1252, and flags Western 12m³ (incomplete fix of w5/529)](./713.md)
- [714 — An NFD --account the ledger does not open is remembered, then blocks flag-free imports](./714.md)
- [715 — Settings notes still missing from three flag-free refusals, now added to a typed one (incomplete fix of w5/525)](./715.md)
- [716 — CSV headers keep direction marks, ZWJ, soft hyphen and NBSP; a zero-width mapping name is now refused (incomplete fix of w5/531)](./716.md)
- [717 — A CSV decode error past 8 KiB names the wrong byte offset](./717.md)
- [718 — A bea write to an include in another directory makes add/import exit 4 instead of queueing](./718.md)
- [719 — Staging copies left by a killed engine are not cleared by the next write (one-hour sweep, target directory only)](./719.md)
- [720 — --partial is still superlinear with several bad rows, and slower than before on a mixed batch (incomplete fix of w5/537)](./720.md)
- [721 — The NFD --into spelling that created a file is refused the second time (regression from w5/536)](./721.md)
- [722 — 1.234,56 and bulk amounts still get raw parser text; tag/link refusal wording (incomplete fix of w5/534)](./722.md)
- [723 — treeify: a BOM splits the tree; /dev/stdin and FIFOs still give a raw UnicodeDecodeError (incomplete fix of w5/535)](./723.md)
- [724 — PYTHONIOENCODING=utf-16 makes bea call a healthy engine damaged and say to delete it](./724.md)
- [725 — A ledger with its own error is told "Pass --partial", which then blames every row](./725.md)
- [726 — The BQL error caret ignores the display width of wide characters](./726.md)
- [727 — A quoted --meta value followed by "; comment" drops the comment and applies C-style escapes (incomplete fix of w5/128/232)](./727.md)
- [728 — An importer's dict or Inventory metadata value is silently dropped on import --apply](./728.md)
- [729 — add custom refuses a negative-zero amount or number value](./729.md)
- [730 — Bulk add moves every same-day sale after every purchase: valid batches refused, wrong lot closed under LIFO/FIFO (regression from w5/543)](./730.md)
- [731 — In bea ask, Ctrl-C between approval panels leaves queued writes running; a write lands after cancel and Ctrl-D hangs (incomplete fix of w5/544)](./731.md)
- [732 — Other booking failures (HOOL {0 USD}, EUR @ 0 USD) still fail with a bare Python error (incomplete fix of w5/538)](./732.md)
- [733 — A sale's escaped lot label no longer selects a control-character lot; JSON echo shows the raw label (incomplete fix of w5/542)](./733.md)
- [734 — In bea ask, Ctrl-C right after Enter can end the session with exit 130](./734.md)
- [735 — A refused JSON float's hint quotes repr(float), not the number typed; following it can unbalance a transaction](./735.md)
- [736 — add transactions --from ./- and format ./- read stdin instead of the file named -](./736.md)
- [737 — --from /dev/stdin waits on the terminal under --json/--no-input (gap in w5/210)](./737.md)
- [738 — Four input-refusal messages are wrong (BOM offset, NUL as UTF-16, --from empty advice, tagged meta TypeError)](./738.md)
- [739 — ask answers turn &#x202E; character references into raw bidi overrides; link reference definitions vanish (gap in w5/548)](./739.md)
- [740 — A later quote changes an earlier valuation; ties settled by line number; double-inversion residue (incomplete fix of w5/556)](./740.md)
- [741 — Import writes a reciprocal add price refuses; add price silent against implicit_prices; exact-1 agreement (incomplete fix of w5/556)](./741.md)
- [742 — Compound-cost buys share an import-id; dedup.md's "sorted order" differs from bea's (incomplete fix of w5/349/555)](./742.md)
- [743 — Reconcile skill: the red-ledger batch "passes on its own" is false while a mismatch remains (incomplete fix of w5/554)](./743.md)
- [744 — ask BQL tool: a NUL kills the question; a dash-leading query is parsed as an engine option (gap in w5/549)](./744.md)
- [745 — ask: content_filter partial answers print as complete; false gzip sent 3x; raw Pydantic warning (incomplete fix of w5/546/547)](./745.md)
- [746 — .run * stops at an empty-window stored query without naming it; bare-CLOSE advice drops rows (incomplete fix of w5/559)](./746.md)
- [747 — Query regex pre-check refuses ?~ subjects and concatenated ~ patterns (adjacent to w5/558)](./747.md)
- [748 — Dated missing-price wording from a sold or later USD-cost lot (incomplete fix of w5/557)](./748.md)
- [749 — .describe Accounts (wrong case or unknown name) exits 0 with no output](./749.md)
- [750 — bea ask cuts digits and account names in answer tables with … at 80 columns, even in --print > FILE; COLUMNS=0 prints nothing](./750.md)
- [751 — bea query text tables misalign rows holding CJK text (padded by character count)](./751.md)
- [752 — import --help splits the --csv example mid-word; 13 sub-command help rows end in ...](./752.md)
- [753 — Whole amounts with dot thousands (ISK, CLP, VND) are refused, or imported 1000x too small with exit 0](./753.md)
- [754 — Editing the previewed CSV drops its sign=ledger on a flag-free --apply, flipping every amount](./754.md)
- [755 — A DEBIT/CREDIT Type column cannot be mapped and is ignored, booking debits as money in](./755.md)
- [756 — The csv:sha256 import-id hashes a tab as \X09, not collapsed whitespace](./756.md)
- [757 — £ and ₩ are treated as GBP/KRW only; GIP, FKP, SHP, EGP and KPW exports are refused](./757.md)
- [758 — Bank-export framing (preamble, sep=, repeated header, footer) cannot be imported; refusal advice cannot work](./758.md)
- [759 — format refuses #tag/0 and ^link/0 as division by zero; 100/(0) still kills the batch (regression/incomplete fix of w5/565)](./759.md)
- [760 — Four query shapes still leak raw Python errors (ORDER BY mixed meta, DISTINCT subquery set, joinstr(accounts), DISTINCT meta)](./760.md)
- [761 — check --auto --cache-filename leaks bean-check's raw WARNING:root line](./761.md)
- [762 — price export leaves out a plugin found via an included insert_pythonpath; the snapshot fails check (gap in w5/094)](./762.md)
- [763 — beancount-options skill: "{} matches any held lot" is false under STRICT; template refused under sellgains/pedantic](./763.md)
- [764 — Under option booking_method AVERAGE, add open makes an unsellable account; the sale hint blames the open (gap in w5/162)](./764.md)
- [765 — A documents-folder file dated before an open makes add open fail with main.bean:0 and no file named](./765.md)
- [766 — Three option gaps: pedantic price --force, plugin_processing_mode raw in exports, invalid name_* value blocks adds](./766.md)
- [767 — doctor context/region with a bare line find nothing through a symlinked path (regression from w5/568)](./767.md)
- [768 — doctor linked/region print inferred-only legs at max precision and 26 decimals under --conversion (w5/571 follow-ups)](./768.md)
- [769 — treeify: renamed roots still lose to a narration colon; the new lookahead is quadratic (incomplete fix of w5/570)](./769.md)
- [770 — doctor roundtrip still prints tracebacks for identical entries and an over-long scratch name](./770.md)
- [771 — check_drained close hint blames the parent for a subaccount's money; following it leaves wrong books](./771.md)
- [772 — A backdated close (or late open) blames the existing entry, cites a line past EOF, and suggests --allow-errors](./772.md)
- [773 — Closed-account hints: add open never names the close, doctor says reopen, duplicate close is bare or misblamed](./773.md)
- [774 — An overlay is still the root with a forecast plugin, a repeated Fava option, above a leaf, and in hints (incomplete fix of w5/578)](./774.md)
- [775 — Two roots including one leaf: writes are judged by whichever sorts first (w5/578 addendum not implemented)](./775.md)
- [776 — With a managed price include, BEANCOUNT_DISABLE_LOAD_CACHE and check --no-cache cannot bypass a stale cache (new with w5/576)](./776.md)
- [777 — beancount-migrate derives the opening from today's balance but asserts it at the export's end; post-export activity is absorbed silently](./777.md)
- [778 — beancount-migrate endpoint assertion fails on a lagged card payment; review/residual accounts never opened](./778.md)
- [779 — dedup.md hashes a separate payee column; migrate's QBO/Monarch references do not, so later bank imports double-book](./779.md)
- [780 — importer-author identify() template crashes the runner on Latin-1 files; bea names no importer](./780.md)
- [781 — Default importers.py shadows the importers/ folder importer-author proposes; the hint is wrong](./781.md)
- [782 — The load cache freezes a date-dependent plugin's output (amortize_over): today's row stays missing until a file changes](./782.md)
- [783 — import --date-format without a year books rows in 1900 and advises re-dating the open to 1900](./783.md)
- [784 — First use: text check and doctor install twice after a failure, and exit 1 with a stale failure after ready](./784.md)
- [785 — A damaged engine still gives raw tracebacks from text check, doctor and example; engine enable reports success (incomplete fix of w5/320)](./785.md)
- [786 — SIGTERM during first-use provisioning orphans uv and leaves a 25 MB partial engine (gap in w5/437)](./786.md)
- [787 — First-use lock: unwritable data dir gives raw Errno 13 exit 1; a waiter on another install waits silently forever](./787.md)
- [788 — First-run polish: no remedy on failed install, uninstall leaves the engine, PyPI license links 404](./788.md)
- [789 — The valuation/translation adjustment differs with and without -t: the FX gain moves to an Equity:Conversions line](./789.md)
- [790 — A -t period holding no foreign currency is refused for a missing price left by an earlier settled trade](./790.md)
- [791 — query --source with $VAR in the path silently queries the expanded (other) ledger; -o replaces the export](./791.md)
- [792 — Descriptor paths after w5/582: --rules /dev/stdin is remembered as /dev/fd/0; /dev/fd/N files get misleading errors](./792.md)
- [793 — A ledger in an untraversable directory gives raw Errno 13, exit 1, not the documented exit 2](./793.md)
- [794 — example -o and price export -o with $VAR create a ledger every later command refuses (incomplete fix of w5/579)](./794.md)
- [795 — Three path gaps: symlinked-root format/add targets, init loop/illegal-byte OSError, -o /dev/stdout to a file](./795.md)
- [796 — A wrong second-currency add balance is silently filled by an old, already used pad (backdated), exit 0](./796.md)
- [797 — add balance --pad-from blames a consumed pad as "already fills"; its remedy then fails (gap in w1/116)](./797.md)
- [798 — import --apply --allow-errors writes a pad-only batch that leaves check failing (incomplete fix of w5/081)](./798.md)
- [799 — Pad hints: staged-pad hint loops, pad-leg currency hint, self-pad accepted](./799.md)
- [800 — A posting with a cost but no commodity (3 {80}) is written as 3 USD {80}, exit 0 (incomplete fix of w5/098)](./800.md)
- [801 — add transaction --json answers that add transactions cannot replay (units-less, # interpolation)](./801.md)
- [802 — @@ 100USD (glued currency) is written as a repeating unit price (gap in w5/059)](./802.md)
- [803 — {100 # USD} beside an omitted amount crashes with AttributeError MISSING copy_sign](./803.md)
- [804 — A defaulted currency gets FX advice for an exchange the user never made](./804.md)
- [805 — Posting slips: {{240}} refused as not one token, empty label dropped, bulk shorthand wording](./805.md)
- [806 — A Fava collapse-pattern/insert-entry regex raising OverflowError or RecursionError blocks reports (gap in w5/091)](./806.md)
- [807 — A misspelled fiscal-year-end option silently makes FY2026 the calendar year (gap in w5/147)](./807.md)
- [808 — Fiscal-quarter refusals: hard-coded FY2027, first declaration cited, refused-period hint (gap in w5/329)](./808.md)
- [809 — fiscal-year-end "00-31" accepted; USAGE never says other Fava options are ignored](./809.md)
- [810 — bea ask follows a symlinked ask_history (chmods and appends to the target); a FIFO there gives no prompt](./810.md)
- [811 — An invalid stored token reads as not logged in or env-var advice, and logout keeps the file; config-dir loop blamed on credential](./811.md)
- [812 — cloud logout exits 1 on a 401 without the error envelope (USAGE says a 401 exits 0)](./812.md)
- [813 — bea init asks every question before refusing an impossible target; --currency message unnamed (incomplete fix of w5/588)](./813.md)
- [814 — `price export -o txns/p.bean` under `include "txns/*.bean"` exports into a directory the glob then loads as an include](./814.md)
- [815 — engine status calls a healthy engine damaged (and says to remove it) when its probe cannot be spawned](./815.md)
- [816 — Spawn failures print a bare errno; SIGXCPU is blamed on an OOM killer, timeout or kill](./816.md)
- [817 — A path component over 255 bytes gives raw Errno 63 for -f, -o and --into (gap in w5/410)](./817.md)
- [818 — Re-imports broken by w5/598: own sub-account entries held as transfer duplicates; import-id-2 no longer matches (regression)](./818.md)
- [819 — doctor missing-open/linked answer exit 0 on a partial load with a missing include (incomplete fix of w5/596)](./819.md)
- [820 — Invalid-UTF-8 importer record blocks import; a mode-000 lock file is blamed on the directory (w5/592/593 gaps)](./820.md)
- [821 — One transfer is the other side of every same-amount row within 3 days; skip loses a deposit, include double-books (new with w5/600)](./821.md)
- [822 — Reused references after w5/599: a distant ID hit hides the same-day twin; latest entry decides conflict](./822.md)
- [823 — A migrated digest with an underscore source name (lunch_money:) is not recognised; row rewritten (gap in w5/601)](./823.md)
- [824 — A payee row meeting a payee-less entry on narration is told "Date, payee … match"](./824.md)
- [825 — A stop 0–20 ms after a write commits still kills bea silently; retry duplicates; format -i keeps rewriting (regression of w5/606)](./825.md)
- [826 — A stopped price export leaves a partial snapshot and dies silently; retry demands --force](./826.md)
- [827 — --pad-from pads a positive balance on a zero-history liability with no sign warning (gap in w5/611)](./827.md)
- [828 — A refused or partial write through an included file never shows the checked-against-root note (gap in w5/613)](./828.md)
- [829 — report -a with a CJK/Thai/emoji leaf also counts sibling accounts that start with it; wrong totals, exit 0](./829.md)
- [830 — A CSV category cell naming a loader-valid account (Thai, CJK leaf) goes to Uncategorized (gap in w5/203)](./830.md)
- [831 — Pending rows after w5/614: refusals lack the status= hint, inference reads left-out rows, hold/declined imported](./831.md)
- [832 — Importer rows with generated csv:sha256 ids are told "only one of them carries a bank ID" (gap in w5/615)](./832.md)
- [833 — list document paths are relative to their include with no source, so two attachments list identically](./833.md)
- [834 — list --details spells TABs as \\x09 and drops line breaks, unlike the ledger](./834.md)
- [835 — list --tag/--link repeated are an undocumented AND; the refusal advice then finds nothing](./835.md)
- [836 — An explicit list --limit 50 still says "pass --limit for more" (gap in w3/325)](./836.md)
- [837 — From a deleted cwd, any refusal with a printed remedy dies with a bare FileNotFoundError (regression from w5/619)](./837.md)
- [838 — Three printed remedies still drop --file or --json (add commodity, query .tables/.help, check FILE)](./838.md)
- [839 — Misplaced-option hints still dead-end: doctor list-options, doctor -f before the op, price forward --json](./839.md)
- [840 — The "already has N errors" refusal suggests the account being added and cites an unwritten line](./840.md)
- [841 — On a ledger with no commodity, import advises --csv currency=CODE, which the next run refuses](./841.md)
- [842 — A period starting 0001-01-01 is refused (-t 0001, BQL OPEN ON 0001-01-01), unlike the 9999 boundary](./842.md)
- [843 — list prints its empty notice on stdout; a BOM-only file gets two leading newlines on first append](./843.md)

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
