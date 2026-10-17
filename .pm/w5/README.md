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
- [589 — A FIFO or deeply nested `credentials.json` hangs or fails every local command](./589.md)
- [590 — `update-check.json` is written through a symlink, overwriting a file outside the config dir](./590.md)
- [591 — Non-regular entries in bea's own load-cache and managed-price cache crash or hang reads (gap in w5/417/418)](./591.md)
- [592 — A corrupt remembered-importer record blocks a plain CSV import with a pathless refusal](./592.md)
- [593 — A FIFO lock file fails `add` with `UnsupportedOperation`; a directory is blamed on the lock dir](./593.md)
- [594 — A second file's preview drops the first file's remembered `sign=ledger`; flag-free `--apply` writes the opposite sign (gap in w1/150)](./594.md)
- [595 — `-o Txns/…` (case variant of a glob-included dir) joins the ledger and doubles balances on APFS (gap in w5/072)](./595.md)
- [596 — `doctor missing-open` exits 0 with a partial list on a ledger with a syntax error](./596.md)
- [597 — `list price -c A -c B` gives `add price`'s `--amount` hint](./597.md)
- [598 — A bank ID from one account dedupes another account's rows through a transfer: a real deposit is skipped as an exact duplicate](./598.md)
- [599 — A monthly autopay reusing one reference is silently skipped across separate exports (gap in w5/075)](./599.md)
- [600 — A transfer imported from both banks is double-booked when their descriptions differ; the import skill promises a fuzzy flag that cannot fire](./600.md)
- [601 — Migrated `<source>:sha256:` ids are matched only for four prefixes, so the generic migrate path double-books overlaps](./601.md)
- [602 — A one-description row is never a possible duplicate of a ledger entry with a payee](./602.md)
- [603 — A `{}` sale split across lots still conflicts with its booked twin (incomplete fix of w5/467)](./603.md)
- [604 — `--id-key fitId` is folded to `fitid`, disabling dedupe for camelCase keys (regression from w5/469)](./604.md)
- [605 — `init` and writes `--into` a new file always fail on exFAT/FAT volumes (`os.link` unsupported)](./605.md)
- [606 — A stop just after the atomic replace kills bea silently though the write committed; a retry duplicates it](./606.md)
- [607 — Disk-full staging failures are reported as validation failures (`--partial` advice, every row "rejected")](./607.md)
- [608 — SIGTERM/SIGHUP during a frontend `-o` export leaves a full `.bea-*.tmp` copy behind](./608.md)
- [609 — A macOS `._main.bean` AppleDouble file stops `format --check .` / `-i .`](./609.md)
- [610 — Full-disk exports and `init` give non-standard messages; `init` leaves created directories](./610.md)
- [611 — `add balance --pad-from` never reports the padded amount; a sign-flipped liability is silently padded by twice the balance](./611.md)
- [612 — Two import refusals still suggest `--account Assets:Checking` (gap in w5/470)](./612.md)
- [613 — A write through an included file reports it as `target.file`, hides the root note from JSON, and keys import memory by the leaf](./613.md)
- [614 — `bea import` cannot leave out Pending rows and the docs are silent; a pending charge that posts differently is double-booked](./614.md)
- [615 — Possible-duplicate reason mentions bank IDs for rows that have none](./615.md)
- [616 — `report -a Expenses:Travel` also matches `Assets:Reimbursable:Expenses:Travel` (component match anywhere; gap in w5/292)](./616.md)
- [617 — Interval series drop plugin transactions in clipped fragments and keep assertion-only empty rows](./617.md)
- [618 — `-t "year - year+1"` refused while `(year) - (year+1)` works (vendored Fava substitution)](./618.md)
- [619 — `add`'s unknown-account fix-up drops `--file`, so pasting it writes another ledger (gap in w5/303)](./619.md)
- [620 — The misplaced-global hint sends `doctor`/`treeify`/`example` users to a dead end (gap in w5/416)](./620.md)
- [621 — A literal tab is refused as an import delimiter, though the refusal recommends it](./621.md)
- [622 — A forced `--delimiter` that does not split the header is reported as a missing column (gap in w3/226)](./622.md)
- [623 — `cloud ledger create --private --public` creates a public ledger; `--dir` without `--clone` ignored](./623.md)
- [624 — Help/doc slips: "Try bean-check --help", login help omits XDG, USAGE treeify example unordered](./624.md)
- [625 — Hosted ledger: an authored price below an ignored line holding a `"` loses to the managed feed (follow-up of w5/476)](./625.md)
- [626 — A padded `--account` filter validates then matches nothing (incomplete fix of w5/473)](./626.md)
- [627 — The no-importer hint lists a QIF/OFX first line as "its columns" (regression from w5/470)](./627.md)
- [628 — The w5/472 decimal message blames the 12-digit limit for any decimal error and tells `--file` users to use `--file`](./628.md)
- [629 — Hosted ledger: managed feed validator accepts metadata after a blank line or column-0 comment (follow-up of w5/478)](./629.md)
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
