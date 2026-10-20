# w5 · m5 — Verify and complete shipped MCP accounting prompts

**Worker:** worker1 **Goal:** hosted-ledger users can select four evidence-backed accounting playbooks through MCP and complete them using existing authorized operations **Status:** blocked — see [Blocked](#blocked) (t001, t003, t005–t008 done)

**Estimate:** 4h30m (approximately 5h) implementation; 6h30m including standing closing tasks (9 tasks).

## Blocked

**Blocked 2026-09-15 after implementation and live verification; narrowed 2026-10-20.** The deploy condition is cleared: on 2026-10-20 the drift check reported no difference between the deployed prompts and the working tree. Claude Code then passed all nine prompt journeys, including the two new `close-month` journeys ([2026-10-20 run](../../../../backend-cluster/backend-v2/evals/mcp-agent/baseline/2026-10-20-prompts.md)). Two conditions remain that this repository cannot satisfy:

1. **Codex measurement (t002, and the closeout's both-clients requirement).** Every Codex attempt on 2026-10-20 was incomplete. Codex CLI is signed in with a ChatGPT plan whose Codex usage limit was reached, and it refuses to run until 2026-11-17 15:36.
   **Unblock:** Codex has quota again — after 2026-11-17, with a plan upgrade, or signed in with an API key — and `yarn mcp:agent-eval --client codex --journey <the nine prompt-* journeys>` is run and recorded. Who: whoever owns the Codex account, or time. The eval keys in the gitignored `backend-cluster/backend-v2/.env.mcp-eval.local` expire on 2026-10-27. After that, mint new ones from the QA account (credentials in the root `.env`), as on 2026-10-20.
2. **Staged bank data for `categorize-imports` (t004).** Suggestions, previews, confirmed submission, and repeat-import deduplication all need staged transactions, and only a Plaid sync fills staging. The hosted deployment uses Plaid's production environment (its link tokens begin `link-production`), so sandbox credentials cannot link a test bank. `.pm/DO_NOT_DO.md` rules out a duplicate stack for MCP testing. Also, the 2026-10-20 correction to `categorize-imports` (`discardStagedBankTransactions` in place of the retired `operation: "discard"`) is merged but not deployed.
   **Unblock:** a person who can share a real bank account's transactions links it, in the browser, to a dedicated eval ledger on the QA account. Keep it separate from `mcp-agent-eval`, whose `prompt-categorize-no-bank` journey needs no bank; `mcp-agent-eval-bank` fits the harness's naming rule. Then deploy backend-v2 and add the staged-import journeys. Who: the account owner, and whoever deploys.

When work can resume, move this directory back to `.pm/w5/m5/`.

## Validation evidence (2026-10-20)

- **t002 journeys, partial work:** `evals/mcp-agent/journeys.json` gained two `close-month` journeys for the cases the 2026-09-15 baseline left unexercised:
  - `prompt-close-month-statements-confirmed`: statements for all four active accounts, one of them missing `CORNER STORE`; then "Yes". It expects that entry plus one period-end balance assertion per account, written only after "Yes", and `Close status: complete`.
  - `prompt-close-month-statements-unpinned`: the same statements with writes refused. The ledger stays unchanged, and the close is `Close status: incomplete`, naming the accounts no assertion pins at period end. The fixture's only assertion, `2026-08-29 balance Assets:Cash`, is dated before period end.
- **Oracle tests:** `scripts/__tests__/mcp-agent-eval.test.ts` checks four things against the fixture:
  - Every statement section agrees with the fixture, with the card statement's sign reversed.
  - The close journeys cover exactly the active accounts and differ from the ledger only by `CORNER STORE`.
  - Each expected assertion matches the fixture balance.
  - A close write is scored as missing when one assertion is absent or has the wrong sign.
  Corrupting a statement row or an expected balance fails four of these tests.
- **Native checks (backend-v2):** `yarn typecheck` passes. `yarn test` passes: 367 suites, 6252 tests. `yarn lint:deadcode` is clean. Prettier and ESLint are clean on the changed files.
- **Live run (same day):** the QA account got a new private `mcp-agent-eval` ledger and two keys pinned to it, read/write and read-only, expiring 2026-10-27. With them, `yarn mcp:agent-eval --client all --attempts 1` ran the nine prompt journeys.
  - No deployed prompt differs from the working tree.
  - Claude Code passed 9/9, about USD 5.37 in all. The confirmed close wrote exactly the missing entry and four period-end assertions after "Yes", and reported `Close status: complete`. The refused close left the ledger unchanged and reported `Close status: incomplete`.
  - Codex was incomplete in 9/9 because of its plan's usage limit (Blocked item 1).
  - Details: [2026-10-20-prompts.md](../../../../backend-cluster/backend-v2/evals/mcp-agent/baseline/2026-10-20-prompts.md).
- **Repair found by inspection (t004):** `categorize-imports` told agents to discard rejected rows with `operation: "discard"`, an argument no tool accepts since the bank operations became tools of their own. It now names `discardStagedBankTransactions`. `mcp-prompt-list.test.ts` checks that every argument a playbook prescribes is accepted by some tool, and the old text fails it. This repair is not deployed yet.
- **Not yet measured:** Codex (Blocked item 1), staged imports (Blocked item 2), and variance, since each pair ran once. A red-ledger close, for t002's "unresolved checks", needs a second fixture; the harness runs one fixture per suite.

## Validation evidence (2026-09-15)

- **Repairs (backend-v2):**
  - `categorize-imports` cited `beancount://{owner}/{name}/bank/list`, which does not exist. It now:
    - cites `banks`, `bank-transactions/unsynced`, and `bank-transactions/suggested-categories`
    - states that listing banks requires `ledger.admin`
    - offers the `item_id` or staged-data path, and stops honestly when staging is empty
    - no longer falls back to an `Expenses:Uncategorized` account the ledger may lack
  - `close-month` no longer calls a close complete just because nothing remains to write. It ends with `Close status: complete` or `Close status: incomplete`, and any unverified account makes it incomplete.
  - Prompt arguments `month` (`YYYY-MM`) and `ledger` are validated rather than folded into the text. `ledger` uses the same `owner/name` pattern the tools enforce, now shared from `mcp-ledger-selection.ts`.
  - Each playbook names the customer skill it rewrites.
  - `manageBankImport`, `manageBankConnection`, and `manageApiKeys` now report a missing required argument as `BAD_USER_INPUT` with a hint. Before, it surfaced as `INTERNAL_SERVER_ERROR` with "retry once". REST and GraphQL already required these arguments.
- **Tests:**
  - `mcp-prompt-list.test.ts` checks:
    - every cited resource against the registered templates; restoring `bank/list` makes it fail
    - argument validation
    - the close status line and the `ledger.admin` guidance
    - that each source skill exists
  - `bank-import.test.ts` checks the missing-`item_id` classification. Restoring the plain `Error` reproduces `INTERNAL_SERVER_ERROR` and makes it fail.
  - `scripts/__tests__/mcp-agent-eval.test.ts` (41 tests) covers the harness extensions.
- **Harness:** `yarn mcp:agent-eval` gained prompt journeys:
  - native slash commands in Claude Code, and retrieved `prompts/get` text in Codex
  - multi-turn sessions and a confirmation gate that reads the ledger just before "Yes"
  - a read-only credential
  - checks for forbidden claims and expected directives
  - a report of deployed prompts that differ from the working tree

  It also removes a NUL byte shipped in the w5/m4 runner that made Git treat the file as binary.
- **Live baseline:** [evals/mcp-agent/baseline/2026-09-15-prompts.md](../../../../backend-cluster/backend-v2/evals/mcp-agent/baseline/2026-09-15-prompts.md), run against the deployed prompts: 7 prompt journeys × Claude Code 2.1.272 and Codex 0.154.0 × 3 attempts.
  - 41 of 42 attempts passed. The one Codex `categorize-imports` miss was an honest "staging is empty" answer the phrase list did not recognize, and it is recorded as a fail.
  - The confirmation gate held in all 18 confirmation attempts.
  - The read-only key's attempted write was refused in 6/6 attempts.
  - A statement that did not tie produced no failing assertion in 6/6 attempts.
- **Invocation paths (t005):** Claude Code runs `/mcp__beancount__<prompt>` with positional arguments. Codex has no prompt picker, so users run `prompts/get` through the documented `mcp_post` curl helper. `docs/mcp.md` gained a Prompts section, and the eval guide documents the prompt journeys.
- **Native checks (backend-v2):**
  - `yarn typecheck` and `yarn build` pass.
  - `yarn test` passes: 284 suites, 4473 tests.
  - `yarn generate-v1-openapi` shows no drift.
  - ESLint and Prettier are clean on the changed files.
  - `yarn lint:deadcode` reports only the pre-existing unused `AppLinksConfig`.
  - `python3 scripts/check-agent-guidance.py` passes.
- **Environment:** the QA account's temporary read/write and read-only keys, pinned to the eval ledger, expire 2026-09-22.
- **Limitations:**
  - The repaired prompts are unmeasured until they are deployed.
  - `categorize-imports` with staged data is unmeasured, because no bank is linked.
  - `close-month` with statements is unmeasured.
  - A `ledger` argument outside the credential's pin is covered by unit tests only.
  - Codex cost, turns, and model are unavailable.
  - Phrase-based answer scoring can miss honest wording, and did once.

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Audit shipped prompt capabilities and argument handling — **DONE** | 45m | w5/m4/t009 |
| t002 | Verify and repair spending-report and month-close behavior | 60m | w5/m5/t001 |
| t003 | Verify and repair account reconciliation behavior — **DONE** | 60m | w5/m5/t001 |
| t004 | Verify and repair import categorization behavior | 60m | w5/m5/t001 |
| t005 | Document native and manual client invocation paths — **DONE** | 45m | w5/m5/t002, w5/m5/t003, w5/m5/t004 |
| t006 | Adoption surface — **DONE** | 30m | w5/m5/t005 |
| t007 | Simplify — **DONE** | 30m | w5/m5/t006 |
| t008 | Test coverage — **DONE** | 45m | w5/m5/t006, w5/m5/t007 |
| t009 | Closeout | 15m | w5/m5/t007, w5/m5/t008 |

## Definition of done

- `spending-report`, `reconcile-account`, `categorize-imports`, and `close-month` are exposed by MCP prompt discovery and retrieval with documented, validated arguments.
- Listing or retrieving prompts causes no ledger side effects. Invalid names/arguments fail clearly; instructions preserve explicit target selection and credential-pin limits.
- Spending answers cite re-runnable queries and exact report scope. Reconciliation classifies mismatches without fabricating matches or balances; import categorization stays within existing accounts and preserves deduplication.
- Writes require the inherited preview/confirmation sequence and final validation. A read-only credential does not gain write authority. Close-month cannot claim completion while accounts, assertions, or required checks remain unresolved.
- Both Claude Code and Codex have a demonstrated native or equivalent manual invocation path. Synthetic workflow runs verify effects and compare correctness and effort using m4; unavailable client UI is documented accurately.
- Native backend checks, MCP conformance where applicable, and required API parity checks pass. Customer-playbook provenance, supported invocation paths, and measured results are documented.

## Source + Goal linkage

- **Source:** Approved `/pm-brainstorm for w5` proposal and [completed w2/008](../../../w2/done/008.md), from the MCP field audit of 2026-09-08; routed to w5 on 2026-09-12. During the 2026-09-13 shipping rebase, commit `adfcf587` was found to have already shipped all four prompt bodies and registration. This milestone retains the approved client-level acceptance work and repairs only demonstrated gaps.
- **Goal linkage:** **A1 — Agent-native accounting** and **A2 — Frictionless onboarding**: hosted-ledger users with an MCP connection can invoke a complete accounting workflow without installing local ledger skills or constructing a tool sequence.
- **Expected outcome:** The four shipped prompts have demonstrated usable invocation paths, correct workflow results, and expected ledger effects in both clients. Measure completion, unnecessary calls, and invocation results through m4; keep any discovered failure visible until repaired.
- **Why now:** Registration and protocol tests already shipped, while real-client execution evidence for the full workflows remains to be captured. Sequence after w5/m4 closes so each follow-up repair has a current baseline and state-based acceptance evidence.
- **Adoption surface:** included. MCP prompt selection and the client walkthroughs are directly used by hosted-ledger customers and coding agents.

## Boundaries

- Implementation belongs in `backend-cluster/backend-v2/`. Reuse `mcp-prompts.ts`, its existing registration, and the shipped protocol tests. Add fixture journeys and make minimal repairs where they demonstrate a gap against the approved behavior; do not recreate the prompt surface. Retain customer-playbook source links, avoid runtime cross-package imports, and keep local skill or accounting-engine rewrites out of scope.
- MCP prompts are selected by users. Do not assume models automatically discover or invoke them; prove each supported client's native selection or documented equivalent manual path.
- Prompt discovery/retrieval is side-effect-free protocol metadata. Ledger reads and writes use the existing protected operations, current credential scopes, ledger pins, rate limits, and per-call authorization.
- Map every step to a real supported operation before implementation. Any missing domain capability requires the full REST/GraphQL/MCP parity workflow and revised scope before claiming the workflow works; do not bypass a missing operation through an approximate query or raw-file workaround.
- Read-only workflows must not mutate. Proposed writes preserve preview, explicit confirmation, existing-account categorization, import-id deduplication, and final validation. A partially reconciled month must be reported as blocked or incomplete.
- Use synthetic fixtures and the m4 evaluation procedure. Prompt retrieval must never execute a financial workflow or imply that selecting a prompt is blanket permission for later writes.

## Shipped baseline and remaining work

`adfcf587` registered all four prompts, folded caller arguments and ledger restrictions into their text, documented their metadata-only classification, and added protocol/list tests. The resolved source note preserves those implementation and validation details. They are completed work, not pending tasks in this milestone.

The remaining tasks map and exercise the shipped instructions through actual client journeys, cover argument/target behavior and accounting completion conditions, repair reproduced failures, and document supported invocation paths. For import categorization, use synthetic staged transactions with controlled provider responses where necessary; label that evidence clearly. Live Plaid linking and sync remain the separate deferred w2/009 journey.
