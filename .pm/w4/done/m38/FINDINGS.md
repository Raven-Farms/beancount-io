# Early-year directive dates are falsely refused as non-calendar dates

**Minor · backend-v2.** Production `https://beancount.io`, 2026-10-20, local main `9c9eb7150`; full deployed backend revision unverified. Found during the owned headless dashboard QA run through its authenticated API controls. The QA owner has admin/push access to the designated disposable synthetic ledger. Credentials stayed in the existing helper/session; public reproductions use `<qa-owner>/<synthetic-ledger>`.

## Live structured-write boundary

Send the real GraphQL bulkEntries mutation with one OPEN entry, currencies USD and a unique prefixed account. The only changed field between the date cases is the explicit date/account suffix:

```json
{"ledgerId":"<qa-owner>/<synthetic-ledger>","entries":[{"type":"OPEN","open":{"date":"0099-01-01","account":"Assets:Qa-20261020:Date-0099","currencies":["USD"]}}]}
```

| date | real response | file effect |
| --- | --- | --- |
| 0001-01-01 | HTTP 200, GraphQL BAD_USER_INPUT: entry 0 date is not a calendar date; use YYYY-MM-DD | exact original file unchanged |
| 0099-01-01 | same false refusal | exact original file unchanged |
| 0100-01-01 | HTTP 200, success:true, Added 1 entry successfully | exactly one own open directive with the correct 0100 date; immediately restored |

The accepted control's real source is `0100-01-01 open Assets:Qa-20261020:Date-0100 USD` (with formatter alignment). No 1900 remapping or duplicate write was observed in that accepted case. An earlier multi-entry setup also failed atomically at its first 0099 open date, with no source change.

## Independent text-write and ledger controls

Both `appendLedgerText(...,dryRun:true)` in GraphQL and `POST /api-gateway/v1/ledgers/<qa-owner>/<synthetic-ledger>/directives/text` with `{text,dryRun:true}` reproduce the same cutoff:

- `0099-01-01 open Assets:Qa-20261020:Append-Date-0099 USD` is BAD_USER_INPUT; REST uses HTTP 400 and GraphQL its normal HTTP 200 error envelope.
- The otherwise equivalent 0100 directive succeeds, returns dryRun:true/count 1/errorsBefore 0/errorsAfter 0, and leaves the file byte-for-byte unchanged.

These dates are supported ledger inputs. An isolated rustledger parse accepts a fixture with 0099 account opens/transaction and a 2026 transaction without errors. The same four prefixed directives were appended through the existing file-source API: the genuine hosted ledger check has zero errors, BQL returns the exact 0099-08-11/3.75 and 2026-10-20/1.25 rows, and Income Statement reads for 0099 and 0099-08 return the correct 0099 date buckets and 3.75 USD. A day filter and its explicit 2026-10-20 control both return 1.25 USD. The source fixture was then restored exactly.

The first browser report-document navigation with that source fixture timed out before rendering, so no completed dashboard export or ordinary CSV booking is claimed. That timeout's cause is unclassified and is not part of this finding. The source fixture was immediately restored. The API rejection and its accepted 0100 control were independently repeated after that restoration.

## Cause and repair boundary

`backend-cluster/backend-v2/src/features/ledger/utils/directive-date.ts:14–30` recognizes the four-digit ISO shape, then constructs `new Date(Date.UTC(year,month-1,day))`. JavaScript remaps numeric years 0–99 into 1900–1999. Its year round-trip therefore fails for valid 0001–0099 and throws the calendar-date error. LedgerEntryService.addBulkEntries calls the helper at :319 before file reads/routing; DirectiveAppendWorkflow calls it at :103 even for dry runs.

Construct and validate the requested UTC calendar year without that special remapping, while preserving existing shape/range/error rules. Keep exact date strings and year-correct date routing through both consumers. Retain the current refusal of year 0000 and malformed/nonexistent dates; do not remove validation or make allowInvalid bypass it. No ledger-engine or dashboard repair substitutes for this shared API boundary.

The two domain consumers feed GraphQL bulkEntries/appendLedgerText, REST entries/directives-text handlers and MCP addLedgerEntries/appendLedgerText. REST/GraphQL text behavior and GraphQL structured behavior were live tested. MCP and REST structured behavior are source-traced, not live verified. Preserve credential-policy exceptions and follow backend-v2's required adapter-parity workflow; a registry entry or mock that only checks delegation is insufficient.

## Dedupe and validation scope

All board states/open milestone summaries were searched for parseDirectiveDate, directive-date, early years,0099, Date.UTC and false calendar refusals. The calendar guard was introduced in `3162f700c` for completed w5/033's invalid-date RangeError. Its malformed-date repair remains correct; its tests cover modern/leap dates but omit the low-year boundary. W4/277 concerns the dashboard CSV formatter's 1901/1999 display and changes a different package. W4/m32's new canonical-string date contract also does not repair this backend guard. No later correction exists in the implicated paths through fetched origin/main `c836386024577b5c53917beac9eb89d04812cc1e`.

Implementation regressions must include valid 0001/0099/0100 dates, a valid early leap year, impossible leap/day/month cases, malformed shape and existing year 0000 refusal. Exercise both write workflows through eligible REST/GraphQL/MCP adapters, with actual returned/source dates, date-routed paths, dry-run effects and atomic validation failure. Keep the parity zero-debt gate, frozen baseline and credential policy intact. Source-only receipt/legacy write callers need audit coverage, not unverified live claims.

## Cleanup and evidence

The raw four-directive source fixture committed in `a7b11b78293bce249ea50976c12a87e2b06e9e27`; restoration `dcb5959d7b297770dcc50a0363418e21a88dcfb4`. The accepted 0100 open control committed in `6c69ecfd23e980aa9703717da61bcb067bfd655c`; restoration `411f66ccc992929f2208b6653be237af00ec9f81`. Every restore used two fresh exact content/blob/path/size/last-commit reads of the owned write. Final verification: only main.bean, 2817 bytes, blob `f1a0b83c1aaf9608113c6bd3174bf7d2dab35407`, exact original bytes, 12 accounts, no prefixed accounts and zero ledger errors. Text dry runs left this same file unchanged. All owned extra contexts are closed.

Ignored dashboard evidence under `dashboard/tmp/qa-20261020/dashboard-loop/`: `directive-date-boundary-complete-control.json`, `directive-date-text-dryrun-control.json`, `report-date-source-seed-control.json`, `report-date-api-summary-control.json` (full response alongside it), and `report-date-boundary-cleanup-control.json`. The local engine probe is `backend-cluster/ledger/tmp/qa-20261020/report-date-boundary-probe.{cjs,json}`. Production MCP, REST structured writes, complete UI booking/export, every date/routing pattern, other engines and the corrected build remain unverified. No product fix was implemented by QA.
