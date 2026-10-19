# Shared `bea` command recipes

Read the sections needed for the current workflow. Prefer `bea` for ledger
operations; the skill owns interpretation, review, and the user's confirmation.
Check `command -v bea` once. If it is absent, suggest
`brew install bex-co/tap/bea` or `uv tool install beancount-io`; the explicit
developer fallback is in beancount-init's `references/compatibility.md`.
If an installed `bea` cannot run its managed engine — provisioning fails, or
the error names the engine rather than the ledger — surface that error and
repair/retry the engine. A nonzero exit carrying bea's JSON error envelope (an
invalid ledger, missing prices, a bad argument) is bea's answer about the
ledger or the request: act on its `message`, `details` and `result`, not on
the engine. Do not install another Beancount CLI or configure private engine paths.

## Hosted ledgers

These skills work on ledger files on this machine. When the user's ledger is
hosted on Beancount.io and its MCP server is connected, do not search for or
create local files: use that server's tools, with the matching server prompt
when one exists.

| Skill | Beancount.io MCP prompt |
| --- | --- |
| beancount-ask | `spending-report` |
| beancount-close | `close-month` |
| beancount-import | `categorize-imports` |
| beancount-reconcile | `reconcile-account` |

The other skills have no hosted prompt; use the server's tools directly. If
the ledger is hosted and the server is not connected, say so and offer the
two ways forward: connect the MCP server, or work on a local clone
(`bea cloud ledger clone`, which needs the account's SSH key).

## Bind the ledger and destination

- Set `ledger` to the discovered **root** ledger's absolute path, including
  when its name is `ledger.beancount` or it is outside the current directory.
- Set `target` to the user-approved write destination, relative to that root's
  directory. For these existing-ledger workflows it must already exist and be
  included by the root. For a root-file write, use its basename as `target`.
- Pass `--file "$ledger"` on every ledger command and `--into "$target"` on
  every directive write. `--file` selects the whole ledger for validation;
  `--into` selects where entries go. Never substitute the included file for
  the root: that would omit accounts, plugins, and assertions in other files.
- Use global `--json --no-input` for machine ledger reads and writes. Inspect the
  exit status, error envelope, notes, and `truncated` indicator; a truncated
  listing is not complete input for deduplication or reconciliation. Query the
  full date window, or increase the listing limit until it is complete.
- `bea ingest` uses native output and rejects `--json`; inspect its actual
  identification and extraction results even when the exit status is 0.

## Read and check

```sh
bea --file "$ledger" --json --no-input query "$query"
bea --file "$ledger" --json --no-input report income-statement --time "$month"
bea --file "$ledger" --json --no-input report balance-sheet --time "$month"
```

A read on a ledger that already fails its check is refused under `--json`
(`Ledger has N error(s). Pass --allow-errors to report anyway.`). When the read
diagnoses that failure — reconciling a failing assertion — pass
`--allow-errors` to the read, and report its `ledger_valid` and
`ledger_errors` to the user. Never pass it to a write to get past a red check.

A report values every row at market in the operating currency, so under
`--json` it exits 1 with `result.missing_prices` when a commodity has no price
— an `@`-priced foreign charge, an option lot. That is a valuation gap, not a
failure: pass `-x at_cost` for book value (lots at cost, unpriced commodities in
their own units), or disclose the missing prices; spending in the currency paid
comes from beancount-ask's `weight` recipes.

Use BQL to enumerate all relevant postings/accounts; `list` defaults to only
50 results. For a human-readable transaction, use `list transaction --details`.
Run the final check against the root, including after writing an included file:

<!-- recipe: check -->
```sh
bea --file "$ledger" --json --no-input check
```

## Open accounts, then write the confirmed batch

Show account opens with the proposal. Their dates must be on or before the
earliest affected transaction, including historical opening balances. Set
`open_target` to the approved file for account definitions (often the root).
Only restrict currencies when that matches the account's intended holdings.

<!-- recipe: open -->
```sh
bea --file "$ledger" --json --no-input add open --date "$open_date" --account "$account" --into "$open_target"
```

A ledger that loads `beancount.plugins.nounused` (or `pedantic`, which runs it)
refuses a new open until something posts to the account: `Unused account
'…'`. That refusal, and only that one, is a documented two-step:

1. Stage the open with the `open-staged` recipe below. Any other error in its
   refusal still means fix the proposal, not stage it.
2. In the same workflow, write the confirmed batch that first posts to the
   account (the `batch` recipe, without `--allow-errors`), then run `check`.

Between the steps the ledger is red for that account alone, so do not stop
there or report the workflow done. If it is interrupted after step 1, resume
by writing that batch before anything else, or tell the user the staged open
is waiting for its first posting.

<!-- recipe: open-staged -->
```sh
bea --file "$ledger" --json --no-input add open --date "$open_date" --account "$account" --into "$open_target" --allow-errors
```

Create the approved JSON array in `batch` (a scratch file), or pass that same
array on stdin using `--from -`. Use decimal **strings**, not floating-point
numbers. Each transaction has `date`, `flag`, optional `payee`, `narration`,
`postings`, optional `meta`, `tags`, and `links`. A cash posting looks like
this complete example; replace the example's native ID with the source row's
actual ID. Follow beancount-import's `references/dedup.md` for hashed IDs.

<!-- recipe: batch-json -->
```json
[
  {
    "date": "2026-05-07",
    "flag": "*",
    "payee": "Coffee Shop",
    "narration": "Card purchase",
    "meta": {"import-id": "ofx:2026050701"},
    "postings": [
      {"account": "Assets:Checking", "units": {"number": "-12.50", "currency": "USD"}},
      {"account": "Expenses:Dining", "units": {"number": "12.50", "currency": "USD"}}
    ]
  }
]
```

<!-- recipe: batch -->
```sh
bea --file "$ledger" --json --no-input add transactions --from "$batch" --into "$target"
```

The batch is validated before writing. Do not use `--partial` or
`--allow-errors` to get an ordinary confirmed batch through a failed check;
the staged open above is the one exception, and it applies to the open only.
`add transactions` **does not deduplicate**, even when `meta.import-id` is
present. Perform the workflow's dedup before writing and before any retry.
Keep `import-id-2` on merged transfers, and preserve pending/uncertain `!` flags.

## One-off entries

For one approved transaction, pass each leg as a native posting and repeat
`--posting` per leg; at most one leg may omit its amount so `bea` balances
it. Set `entry_date`, `payee`, `narration`, and the postings, for example
`posting_1` = `Expenses:Dining 12.50 USD` and `posting_2` = `Assets:Checking`.
Several transactions at once use the `batch` recipe instead.

<!-- recipe: transaction -->
```sh
bea --file "$ledger" --json --no-input add transaction --date "$entry_date" --payee "$payee" --narration "$narration" --posting "$posting_1" --posting "$posting_2" --into "$target"
```

`bea add close` writes even when the account still holds a balance, so read
the balance through `close_date` first and close only an empty account. A
posting dated on the close date is still allowed; a later one is refused.

<!-- recipe: close -->
```sh
bea --file "$ledger" --json --no-input add close --date "$close_date" --account "$account" --into "$open_target"
```

Set `price` to the quote with its currency (e.g. `285.40 USD`). An exact
repeat of a recorded price writes nothing and reports `written: 0`; a second
quote for the same date and commodity needs the user's say-so and `--force`.

<!-- recipe: price -->
```sh
bea --file "$ledger" --json --no-input add price --date "$price_date" --commodity "$commodity" --amount "$price" --into "$target"
```

<!-- recipe: note -->
```sh
bea --file "$ledger" --json --no-input add note --date "$note_date" --account "$account" --message "$note" --into "$target"
```

## Options and investment lots

For explicit per-unit costs, use structured `units` and `cost` in a batch.
For example, after opening the three accounts below, a short put with a
$150 gross premium and $0.65 fee is:

<!-- recipe: option-batch-json -->
```json
[
  {
    "date": "2026-05-07",
    "narration": "Sell put",
    "links": ["option-1"],
    "postings": [
      {"account": "Assets:Checking", "units": {"number": "149.35", "currency": "USD"}},
      {"account": "Assets:Brokerage:Options", "units": {"number": "-1", "currency": "AAPL_PUT_20260620_00150000"}, "cost": {"number": "150.00", "currency": "USD"}},
      {"account": "Expenses:Trading:Fees", "units": {"number": "0.65", "currency": "USD"}}
    ]
  }
]
```

For a disposal with an explicitly selected held lot, carry its actual cost
and optional acquisition date in `cost`. For native booking syntax such as
`{}` or total costs `{{...}}`, use `add transaction --posting`; older `bea`
batch schemas require explicit cost number/currency and accept only plain
amounts in `amount` shorthand. Do not guess a cost to satisfy that schema.

For example, to expire the held short put, set `option_posting` to
`Assets:Brokerage:Options 1 AAPL_PUT_20260620_00150000 {} @ 0 USD`,
`income_account` to the already-open `Income:Trading:OptionPremium`,
`trade_date` to `2026-06-20`, `narration` to `Expire put`, and `trade_link`
to the original `option-1`:

<!-- recipe: option-expiry -->
```sh
bea --file "$ledger" --json --no-input add transaction --date "$trade_date" --narration "$narration" --link "$trade_link" --posting "$option_posting" --posting "$income_account" --into "$target"
```

Repeat `--posting` for the approved cash/fee/stock legs of other events.
Preserve prices, cost dates, tags and links. Omit `units`/`amount` on an
inferred JSON posting, or pass only its account as a native posting.
Confirm unfamiliar shapes with `bea add transactions --help` before writing.

## Assert the statement balance

Set `assertion_date` to the day **after** the statement end, and `amount` to
the statement ending amount in ledger sign, including its currency (e.g.
`987.50 USD`). A liability statement prints the amount owed as positive, so a
card's "New Balance 342.20" is asserted as `-342.20 USD`.
Only write an assertion that the proposed ledger will satisfy.

<!-- recipe: balance -->
```sh
bea --file "$ledger" --json --no-input add balance --date "$assertion_date" --account "$account" --amount "$amount" --into "$target"
```

For an explicitly accepted opening gap with no prior assertion, use
`add balance --pad-from "$equity_account" --pad-date "$pad_date"` with the
same root and destination. Open both accounts on/before the pad date and
place the opening assertion before the period's movements. Reuse the ledger's
existing opening-equity account (`bea init` creates `Equity:OpeningBalances`).
Never use padding to conceal an unresolved transaction mismatch.

## Failure and resume

Account opens, the transaction batch, and assertions are **separate writes**.
Atomicity applies to each command, not the whole workflow. If a later command
fails, report which earlier steps succeeded and inspect the current ledger
before retrying; never blindly replay the transaction batch. A failed
assertion must not be reported as a completed reconciliation.

`bea` has no command for the skills' config comment blocks. Update only the
reviewed comment block after confirmation, preserving other text. This does
not authorize hand-writing directives on the `bea` path.
