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

- [074 — Import crashes on an importer row whose counter-posting has no amount](./074.md) — major CLI importer crash; restricted and unopened counter accounts repeated with an unrestricted control, 20–30m.
- [075 — Import silently skips a later row that repeats an inferred bank reference, and says it is already in the ledger](./075.md) — major CLI missing-transaction bug with an identity-policy owner call; repeated with a renamed-header control, 30–45m.
- [076 — The `add open` remedy for blocked import rows is dated per row, so the first one dead-ends a newest-first export](./076.md) — minor CLI onboarding bug; three-step journey repeated with an earliest-date control, 20–30m.
- [077 — A detected CSV delimiter is remembered and then overrides detection for the next export](./077.md) — minor CLI import bug; comma-then-semicolon exports repeated with fresh-memory and explicit-flag controls, 20–30m.
- [078 — The advised `--csv sign=ledger` discards the remembered mapping instead of applying on top of it](./078.md) — minor CLI import bug; the tool's own advice fails, repeated with a full-mapping control, 30–45m.
- [079 — A multi-file include glob shifts line numbers during write validation, so `--allow-errors` refuses every write](./079.md) — major CLI write bug; root and `--into` refusals repeated with one-match and reordered controls, 45–60m.
- [080 — `add custom --value account:…` is always refused on a ledger with renamed root accounts](./080.md) — major CLI write bug; refusal repeated with default-root and other-directive controls, 30–45m.
- [081 — `--allow-errors` lets a write introduce an Unused Pad error and still exit 0](./081.md) — major CLI exit-contract bug; two shapes leave `check` failing, repeated with flag-free controls, 30–45m.
- [082 — `--meta` drops a leading `#` from a text value and misreports a `name:` value as a bad key](./082.md) — minor CLI metadata bug; silent alteration and false refusal repeated with quoted and bulk controls, 20–30m.
- [083 — Report balance series leave out `U`-flagged transactions that the headline includes](./083.md) — major CLI wrong-number bug; headline and series disagree, checked against BQL with a `!` control, 30m.
- [084 — `bea check` fails with a traceback on the bundled `fava.plugins.*` plugins while `--json check` says valid](./084.md) — major CLI gate bug; human and JSON verdicts split, repeated with an upstream-plugin control, 45m.
- [085 — A `PRINT` export of a ledger with a pad does not pass `bea check`](./085.md) — minor CLI export bug; repeated with a pad-free round-trip control, 30m.
- [086 — A currency conversion in the period keeps the empty trailing interval row the guide says is dropped](./086.md) — minor CLI report bug; repeated with a single-currency control, 20m.
- [087 — Format reads a symlinked root's includes beside the link target, so `-o` overwrites an included file](./087.md) — major CLI output-guard bug; overwrite and false missing-include repeated with regular-file and `query -o` controls, 40–60m.
- [088 — `bea check --auto` fails a ledger that `bean-check --auto` accepts](./088.md) — major CLI regression; compared with upstream and an opened-accounts control, 20–30m.
- [089 — `bea example` and `bea treeify` report upstream usage errors as exit 1](./089.md) — minor CLI exit-code bug; three inputs repeated with exit-2 controls, 20m.
- [090 — `init DIR` and `format -o` leak raw OS errors as exit 1 when the destination cannot be created](./090.md) — minor CLI diagnostics bug; three commands repeated with clean exit-3 controls, 25–35m.
- [091 — `balance` and every report crash with `NotImplementedError` on a ledger carrying Fava's `default-file` option](./091.md) — major CLI report crash; five commands repeated with a fiscal-year option control, 20–30m.
- [092 — A managed price include plus a multi-file include glob shifts line numbers on every read](./092.md) — major CLI silent-wrong-result bug, read twin of 079; hidden entries and duplicate prices repeated against a simulated feed with two controls, 45–60m.
- [093 — A purchase with an omitted cash leg makes every report amount in that currency print the cost's decimals](./093.md) — minor CLI display bug; repeated with an explicit-leg control, 20–30m.
- [094 — `price export` exits 0 for a ledger with a local plugin, and the snapshot fails stock `bean-check`](./094.md) — minor CLI export bug; repeated with a plugin-free control, 30–40m.
- [095 — Read commands need a writable ledger directory once the ledger has a managed price include](./095.md) — minor CLI design-adjacent bug with an owner call; repeated against a simulated feed with a no-include control, 30–45m.
- [096 — A write into a file reached through a `..` include names a nonexistent staging file and `--allow-errors` refuses it](./096.md) — major CLI write bug; repeated with root-write and plain-include controls, 30–45m.
- [097 — `--into` naming a glob-included file in another letter case or Unicode form is reported as a concurrent edit](./097.md) — minor CLI exit-category bug; case and Unicode variants repeated with exact-spelling and literal-include controls, 20–30m.
- [098 — `add transaction` fills a missing commodity on a cost or priced posting with the operating currency](./098.md) — minor CLI silent-wrong-lot bug with an owner call; cost and price variants repeated with an explicit-commodity control, 20–30m.
- [099 — BQL `filename` names vanished staging files on every ledger with a managed price include](./099.md) — major CLI silent-wrong-result bug; offline repro repeated with an include-free control, 30–45m.
- [100 — `price export` of a feed included from two files writes a snapshot that fails `bean-check`](./100.md) — minor CLI export bug against a simulated feed; single-include control passes, 30–40m.
- [101 — `doctor linked` / `region` round the balance tree when the scope mixes whole and fractional amounts](./101.md) — minor CLI display bug with an owner call; remaining half of w3/352, 20–30m.
- [102 — A `PRINT` query that matches no directives exits 2 and tells the user to "use PRINT"](./102.md) — minor CLI exit-category bug; text and JSON modes disagree, empty `SELECT` control passes, 20–30m.
- [103 — An invalid regex in a BQL query exits 1 as a ledger validation failure, and only when a row is scanned](./103.md) — minor CLI exit-category bug; escaped-pattern control passes, 30–40m.
- [104 — `--json query PRINT` emits Python object reprs for `custom` values and `open` booking](./104.md) — minor CLI machine-output bug; `list custom` control shows the clean shape, 30–45m.
- [105 — Set-valued query cells change order between identical runs in JSON and CSV](./105.md) — minor CLI determinism bug; repeated across hash seeds, 15–20m.

The 27 findings from the MCP QA auth sweep against the hosted endpoint (023–054, less the five under [Dropped](#dropped)) were fixed in `backend-cluster/backend-v2` and closed on 2026-10-02 and 2026-10-03; each note under [`done/`](./done/) records what shipped and in which commit. None has been re-observed against the hosted endpoint yet — the fixes reach it with the next backend deploy.

## Blocked inbox

- [015 — Decide the supported way to give a custom importer a third-party dependency](./blocked/015.md) — blocked on the CLI product owner's choice of the supported environment; the new work does not depend on this decision.

## Execution notes

**Approved sequence:** m12 → m13. m12 completed on 2026-09-29 with both installed-agent journeys on published bea 0.3.1; its guide, independent checkpoints, header repair, and sandbox-cache correction are shipped. m13 is parked until a native Windows host is accessible; all eight tasks depend on that baseline, and live-client acceptance additionally needs both native agents authenticated. Neither milestone changes blocked m5 or 015.

Blocked milestones live under `blocked/` with their reason and unblock condition in a `## Blocked` section; they keep their task IDs and return to `wN/mN/` when work can resume.

As of 2026-09-29, m10, m11, m12 and inbox 019–022 are complete. `beancount-io` 0.3.1 (tag `cli-v0.3.1`) is published to PyPI and Homebrew, and the migration journey passed on it in both clients. m9 and inbox 016–018 are complete. m5 and 015 retain their recorded external unblock conditions. w5 remains a general-purpose adoption queue.

The earlier sequence was m3 → m4 → m5. Real-client MCP journeys run against the hosted endpoint, not a duplicate stack. m3 and m4 have no dependency on each other; m5/t001 depends on m4/t009. The customer skill installation work in m3 builds on w1/m21's completed accounting-engine integration. The larger Plaid sandbox journey remains an explicit deferred follow-up in w2/009. m5 verifies and repairs the four prompts already shipped by w2/008; it does not recreate their registration or bodies.

Authenticated CLI live-price milestones m6 → m7 → m8 completed with CLI 0.3.0 on 2026-09-21. The existing m5 blocker remains independent.
