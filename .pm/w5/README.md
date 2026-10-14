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

## Inbox

- [244 — The import preview diff prints existing ledger lines raw, so escape sequences in the ledger's last lines reach the terminal](./244.md) — minor CLI output-safety bug; six raw ESC bytes on a PTY, clean-ledger control emits none, 20–30m.
- [250 — `bea query --source DIR` (or `csv:<missing>`) prints a long traceback of engine source instead of a usage error](./250.md) — minor CLI bug; traceback at exit 1, `--file DIR` control gives a one-line exit 2, fix with 249, 20m.
- [251 — Four `bea doctor` operations exit 245 with no message when the engine crashes on the ledger (regression of w5/done/010)](./251.md) — minor CLI regression; silent exit 245, `doctor context` control names SIGSEGV at exit 1, 20–30m.
- [252 — A write whose engine dies on a signal still reports the raw `(exit -11)` instead of naming the signal](./252.md) — minor CLI message bug; read-path control names SIGSEGV, fix with 251, 15m.
- [253 — `bea query 'help print'` fails with `TypeError: … got 'NoneType'` (the w3/done/299 crash, for the other overridden statement)](./253.md) — minor CLI bug; `help select` control prints help, 10–15m.
- [254 — `import --id-key ID` silently turns off bank-ID matching; only the lowercase spelling `id` is aliased](./254.md) — minor CLI import bug; reused bank id written twice with exit 0, lowercase control exits 4, 15–25m.
- [255 — CSV amounts written with a Unicode minus sign (U+2212) are refused, though w3/done/256 listed them among the spellings to accept](./255.md) — minor CLI import bug; clear exit 2, ASCII-minus control imports, 10–15m.
- [256 — Plain `bea check` still prints a Python traceback for a broken `plugin` line (w3/done/359's own reproduction)](./256.md) — minor CLI bug (owner call, forwarded stock output); `--json check` and `list` controls give the one-line form, 30–40m.
- [257 — A ledger with a deny-delete ACL fails every write with a raw `PermissionError` and leaves a staged copy behind each time (regression of w1/done/073)](./257.md) — minor CLI regression; exit 1 `validation` with a leaked staging copy per attempt, no-ACL control writes, 30m.
- [258 — With stdout closed, `format`, `doctor` and `query --source` exit 1 with `'NoneType' object has no attribute 'write'`](./258.md) — minor CLI bug; `>/dev/null` and `list` controls exit 0, 15m.
- [259 — `bea query --source` with an impossible date literal prints a long traceback instead of the usage error the `--file` path gives](./259.md) — minor CLI bug; traceback at exit 1, `--file` control exits 2 with one line, fix with 250, 15m.
- [260 — A list-valued column next to an aggregate with no `GROUP BY` fails with `TypeError: unhashable type`](./260.md) — minor CLI bug; explicit `GROUP BY` control exits 2 with a clear message, 20m.
- [261 — Without `--time`, report series end on a date after the report's own `as_of`, and the date moves with `--interval`](./261.md) — minor CLI report bug; yearly net-worth point dated 2026-12-31 against `as_of` 2026-02-10, `--time` control dated correctly, 45–60m.
- [262 — A comment after the closing `;` makes a one-statement query fail with "One BQL statement per invocation; got 2"](./262.md) — minor CLI bug; comment-before-semicolon control runs, 20–30m.
- [263 — `add transaction --posting` rounds a negative amount wider than 28 significant digits; the positive twin is written exactly](./263.md) — minor CLI precision bug; negative leg loses a digit at exit 0, 28-digit and bulk controls exact, 40–60m.
- [264 — `bea --help` truncates five command summaries with `...` again (regression of w1/m15/t005)](./264.md) — minor CLI cosmetic regression; five root-help rows end in `...`, originally shortened commands print in full, 15–20m.
- [265 — CSV amounts with the currency symbol before the minus sign (`$-1,234.56`, `€ -1.234,56`) are refused once the number has a separator](./265.md) — minor CLI import bug; clear exit 2, sign-before-symbol control imports, 20–30m.
- [266 — A typed `--delimiter` is refused after a header-inferred import of a semicolon file has been remembered](./266.md) — minor CLI import bug; documented override exits 2, fresh-config control works, fix with 077, 20–30m.
- [267 — An explicit `--csv` re-run silently forgets a remembered `--date-format`, and the next ambiguous export is booked month-first](./267.md) — minor CLI import bug; 4 October written as 2026-04-10 after an unannounced drop, ambiguous-file control names the drop, 20–30m.
- [268 — Under a currency conversion, quiet interval rows give `{}` / `—` for income and expenses instead of the documented `{"USD": "0"}` / `0.00 USD`](./268.md) — minor CLI report bug; net profit zero-filled in the same row but income/expenses are `{}`, 20–30m.
- [269 — `BEA_ENGINE_PYTHON` naming an interpreter without Beancount gives a raw traceback that never names the variable, and `bea add` exits 4 "outcome is unknown"](./269.md) — minor CLI bug; traceback and a false exit 4, `check` control names the variable, 30–45m.
- [270 — Under `--json`, plugin output is discarded, although the docs say it goes to stderr](./270.md) — minor CLI docs/behaviour mismatch (owner call); text-mode control shows both markers on stderr, 15m.
- [271 — `add balance` with a `~` tolerance leaves a formatted ledger failing `format --check`](./271.md) — minor CLI formatting bug; plain-amount control stays formatted, 30–40m.
- [272 — `--meta 'check:1045/0'` crashes the engine: exit 4 "the outcome is unknown"](./272.md) — minor CLI bug; engine crash at exit 4, posting-path control exits 2, fix with 128, 15m.
- [273 — Ctrl-C during `bea check` prints `Aborted!`, though the docs say an interrupt exits 130 without a message](./273.md) — minor CLI cosmetic bug; `query` control is silent, 20–30m.
- [274 — `bea format --check DIR` silently skips a subdirectory it cannot read and reports the tree formatted](./274.md) — minor CLI bug; exit 0 "All 1 file(s) are formatted" with a skipped subtree, readable control exits 1, 30m.
- [275 — `bea example` skips its date-range check for non-ISO dates and fails with `IndexError`](./275.md) — minor CLI bug; ISO-date control exits 2 with the documented message, 15–20m.
- [276 — A stored `query` directive with an empty body makes `.run NAME` and `.run *` fail with `IndexError`](./276.md) — minor CLI bug (contrived); `.run one` control works, 20m.
- [277 — `bea example -o /dev/null` is refused with exit 4 "Already exists", unlike every other `-o` command](./277.md) — minor CLI consistency bug; `query -o /dev/null` control exits 0, 10m.
- [278 — A ledger that is not UTF-8 gets the documented decode error from `format` and `add`, but a raw codec message from read commands](./278.md) — minor CLI message bug; `format` control gives path, offset and remedy, 20–30m.
- [279 — `price export` and `example -o` into an unwritable directory exit 1 with a raw OS error instead of the documented exit 3](./279.md) — minor CLI bug; raw errno at exit 1, `query -o` control exits 3 with the staged-copy message, fix with 090/119, 20–30m.
- [280 — USAGE says `price` rejects JSON mode, but `price status` and `price export` answer with the envelope](./280.md) — minor CLI docs bug; `--json price status` returns an envelope, 5–10m.
- [281 — A remembered `encoding=cp1252` is replayed onto a later UTF-8 export, writing mojibake (`CafÃ© ZÃ¼rich`) with exit 0](./281.md) — major CLI import bug; mojibake written at exit 0, fresh-config control writes the text correctly, 30–45m.
- [282 — Under `--json`, a refused flag-free import does not report the remembered settings it used](./282.md) — minor CLI JSON bug; preview has `remembered`/`date_format`/notes, refused apply has none, 20–30m.
- [283 — The remembered-settings line prints `--csv` twice when an encoding is in force, so pasting it runs a different mapping](./283.md) — minor CLI bug; pasted line swaps payee for an inferred narration mapping, single-`--csv` control keeps it, fix with 195, 15–20m.
- [284 — Under `--json`, a successful `import` does not say that it could not save the import memory](./284.md) — minor CLI JSON bug; text-mode control warns, next flag-free JSON import exits 2, same mechanism as 270/282, 15–20m.
- [285 — A ledger with both a `../` include and a managed price include treats the included file's entries as generated: `--on-disk` hides them and `add price` writes a conflicting quote](./285.md) — major CLI bug (offline simulation); conflicting quote written at exit 0, control without the managed include refuses, 30–45m.
- [286 — `bea doctor` does not resolve managed price includes: `region --conversion value` leaves the holding unvalued and `roundtrip` reports success over a "File glob" error](./286.md) — minor CLI bug (offline simulation); `balance` control values the holding at 82,000 USD, 30–45m.
- [287 — A skill's `SKILL.md` saved as UTF-8 with a BOM is silently never discovered by `bea ask`](./287.md) — minor CLI bug; documented inspection lists only the BOM-less twin, 15–20m.
- [288 — `bea query --source memory:` prints a long traceback, and the bad-scheme error recommends `memory:...`](./288.md) — minor CLI bug; traceback at exit 1 for a scheme the error message itself recommends, fix with 250, 10–15m.
- [289 — `bea query --source F -o FILE ".help"` prints to stdout and replaces the export with an empty file](./289.md) — minor CLI bug; export emptied at exit 0, `--file` control writes the help into the file, fix with 236, 15–20m.
- [290 — `add price` and `init --opening-balance` refuse comma-grouped numbers (`65,432.10 USD`) that `add balance`, `--posting` and stock Beancount accept](./290.md) — minor CLI consistency bug; clear exit 2, `add balance` control accepts the same grouping, same class as 213, 20–30m.
- [291 — The first write into a not-yet-existing `--into` file hides a `../` include: `add price` writes a conflicting quote, and `--allow-errors` refuses over the old error](./291.md) — major CLI write-guard bug; exit 0 with two quotes for one day, existing-file and in-tree include controls refuse correctly, 15–20m with 285.

The 27 findings from the MCP QA auth sweep against the hosted endpoint (023–054, less the five under [Dropped](#dropped)) were fixed in `backend-cluster/backend-v2` and closed on 2026-10-02 and 2026-10-03; each note under [`done/`](./done/) records what shipped and in which commit. None has been re-observed against the hosted endpoint yet — the fixes reach it with the next backend deploy.

## Blocked inbox

- [015 — Decide the supported way to give a custom importer a third-party dependency](./blocked/015.md) — blocked on the CLI product owner's choice of the supported environment; the new work does not depend on this decision.

## Execution notes

**Approved sequence:** m12 → m13. m12 completed on 2026-09-29 with both installed-agent journeys on published bea 0.3.1; its guide, independent checkpoints, header repair, and sandbox-cache correction are shipped. m13 is parked until a native Windows host is accessible; all eight tasks depend on that baseline, and live-client acceptance additionally needs both native agents authenticated. Neither milestone changes blocked m5 or 015.

Blocked milestones live under `blocked/` with their reason and unblock condition in a `## Blocked` section; they keep their task IDs and return to `wN/mN/` when work can resume.

As of 2026-09-29, m10, m11, m12 and inbox 019–022 are complete. `beancount-io` 0.3.1 (tag `cli-v0.3.1`) is published to PyPI and Homebrew, and the migration journey passed on it in both clients. m9 and inbox 016–018 are complete. m5 and 015 retain their recorded external unblock conditions. w5 remains a general-purpose adoption queue.

The earlier sequence was m3 → m4 → m5. Real-client MCP journeys run against the hosted endpoint, not a duplicate stack. m3 and m4 have no dependency on each other; m5/t001 depends on m4/t009. The customer skill installation work in m3 builds on w1/m21's completed accounting-engine integration. The larger Plaid sandbox journey remains an explicit deferred follow-up in w2/009. m5 verifies and repairs the four prompts already shipped by w2/008; it does not recreate their registration or bodies.

Authenticated CLI live-price milestones m6 → m7 → m8 completed with CLI 0.3.0 on 2026-09-21. The existing m5 blocker remains independent.
