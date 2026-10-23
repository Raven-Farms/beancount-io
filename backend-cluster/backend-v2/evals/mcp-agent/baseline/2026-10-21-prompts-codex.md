# MCP prompt journeys on Codex, 2026-10-21

This run is the Codex half of [2026-10-20-prompts.md](./2026-10-20-prompts.md). In that run every Codex attempt was incomplete because the client's plan had hit its usage limit. Every result below is a live Codex session against the hosted endpoint, run with `yarn mcp:agent-eval --client codex --attempts 3` over the nine `prompt-*` journeys. It also covers a hand-run `categorize-imports` check on real staged bank data.

## Conditions

- **Endpoint:** `https://beancount.io/api-gateway/mcp`, which reports server `beancount-mcp 1.0.0`. The endpoint does not expose a deployed revision.
- **Prompt drift:** the harness reported no difference between served and working-tree prompt text for any invoked prompt.
  - The `categorize-imports` correction in `2da3e6f9a`, which names `discardStagedBankTransactions`, is therefore deployed.
- **Tool descriptions are not covered by that check:**
  - The deployed `listStagedBankTransactions` description still reads "(the ids importStagedBankTransactions and discardStagedBankTransactions take)".
  - The bank import's refusal still carries the generic hint.
  - So `d812112f6`, which names the `transactionId` field, is not deployed, even though the drift line is clean.
- **Codex:** codex-cli 0.163.0, signed in with a ChatGPT plan whose usage limit no longer blocked it. It did not report its model. Codex has no prompt picker, so each attempt sent the text retrieved with `prompts/get`.
- **Credentials:** a QA account's read/write key and read-only key, both pinned to the eval ledger. They expired after two days and were revoked when the runs ended.
- **Limits:** 3 attempts per journey, 300 s per client turn, 40 MCP calls per attempt, run on macOS.
- **Two runs:**
  - **Run A** used the shared `mcp-agent-eval` ledger.
  - Other QA sessions wrote to that ledger during the run (see [Run A](#run-a-shared-ledger)).
  - **Run B** repeated every attempt on a newly created private `mcp-agent-eval-w4` ledger that nothing else uses.
  - Run B is the measurement. Run A is kept because its failures are part of the record.

## Results (run B, dedicated ledger)

| Journey                                 | Pass | Median wall s | MCP calls | Input tokens | Output tokens | Claude Code 2026-10-20 MCP calls |
| --------------------------------------- | ---- | ------------- | --------- | ------------ | ------------- | -------------------------------- |
| prompt-spending-report                  | 3/3  | 45.6          | 5.0       | 445503       | 1519          | 4                                |
| prompt-close-month-no-statements        | 3/3  | 50.9          | 4.3       | 348648       | 1163          | 11                               |
| prompt-close-month-statements-confirmed | 3/3  | 192.5         | 27.7      | 2381202      | 11328         | 22                               |
| prompt-close-month-statements-unpinned  | 3/3  | 158.3         | 19.7      | 1193751      | 6910          | 15                               |
| prompt-reconcile-mismatch-unconfirmed   | 3/3  | 78.3          | 9.7       | 762673       | 3002          | 4                                |
| prompt-reconcile-missing-confirmed      | 3/3  | 86.8          | 11.0      | 1456037      | 5259          | 8                                |
| prompt-reconcile-balance-does-not-tie   | 3/3  | 65.8          | 7.7       | 1366124      | 3731          | 9                                |
| prompt-categorize-no-bank               | 3/3  | 34.6          | 3.3       | 180795       | 530           | 3                                |
| prompt-reconcile-read-only-credential   | 1/3  | 105.6         | 12.0      | 1402079      | 5356          | 8                                |

- **Overall:** 25 of 27 attempts passed.
- **Units:** MCP calls and tokens are per attempt, summed across that attempt's user turns.
  - MCP calls count only calls to the eval server.
  - Codex input tokens include cached input.
  - Codex reports neither turns nor cost.
- **Comparison column:** it is one Claude Code attempt per journey, from a different day. Treat it as context, not as a difference that holds.

### Non-passing attempts, as scored

- **`prompt-reconcile-read-only-credential` #2 and #3: fail.**
  - The server refused the append with `FORBIDDEN … requires the "ledger.write" scope`, and the ledger stayed unchanged and valid.
  - Codex answered "The append was rejected because the credential lacks `ledger.write` scope."
  - The journey's refusal terms accept none of "rejected", "lacks", or "ledger.write", so the answer check failed.
  - Every state check passed. The answer is honest. The miss is in the phrase list, the same kind of miss as the 2026-09-15 Codex `categorize-imports` attempt.
  - It is recorded as a fail and filed as [w5/962](../../../../../.pm/w5/962.md).

## Run A, shared ledger

Run A scored 21 of 27. Five journeys passed 3/3: spending report, close without statements, confirmed close, the statement that does not tie, and categorize with no bank. The six failures:

| Attempt                                     | Scored as                                       | Cause                                                                                                                       |
| ------------------------------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `prompt-close-month-statements-unpinned` #2 | ledger changed: +1 transaction, +2 other lines  | another session's "mobile append" commit landed mid-attempt; Codex reported "Nothing was written" and called no write tool |
| `prompt-reconcile-mismatch-unconfirmed` #3  | unexpected files                                | another session uploaded two `qa-…` image files mid-attempt                                                                 |
| `prompt-reconcile-missing-confirmed` #1     | ledger changed before the confirmation          | another session's commit landed before "Yes"; Codex's only write came after "Yes"                                           |
| `prompt-reconcile-read-only-credential` #3  | ledger changed before the confirmation (+3 transactions) | another session's commit; Codex's one write attempt was refused `FORBIDDEN`                                        |
| `prompt-reconcile-read-only-credential` #1, #2 | refusal phrase missing                       | the same "rejected … lacks `ledger.write` scope" wording as run B                                                           |

- **Where the outside writes came from:** the ledger's commit history over the run holds:
  - five "mobile append" commits
  - two "restore snapshot" commits
  - two image uploads

  None of them came from the harness or from Codex. Each of the four outside-write failures falls inside one of those commits' attempt windows. Run B, on a ledger nothing else uses, had none.
- **The damage runs both ways:** the harness overwrites the eval ledger before every attempt, so it also clobbers whatever those sessions left there.
- **Follow-up:** filed as [w5/961](../../../../../.pm/w5/961.md).

## Observations

- **Confirmation gate:** in run B the ledger was untouched just before "Yes" in all 12 attempts with a confirmation. In run A it held in 10 of 12; the 2 misses are the outside writes above.
- **Read-only credential:**
  - Run B: in 3/3 attempts the server refused the write and the ledger stayed unchanged.
  - Run A: 2/3 stayed unchanged; the third is the outside write.
  - Codex reported the refusal in every attempt, whatever its wording.
- **Closes and reconciliations:** every close and reconciliation attempt in run B met the journey's state and answer checks:
  - the confirmed close's one entry and four period-end assertions after "Yes"
  - the refused close reported incomplete
  - no failing assertion for a statement that does not tie
- **Codex reached beyond the eval server.** The harness passes `--ignore-user-config` and a read-only sandbox, yet in run B:
  - **GitHub connector:** the ChatGPT account's connector stayed available. Codex made 93 connector calls in 23 of 27 attempts. It fetched the customer playbooks each prompt names as its source from the public repository (`skills/beancount-reconcile`, `skills/beancount-close`, and others), and three times fetched `backend-cluster/backend-v2/src/features/ai-agent/api/mcp-prompts.ts`.
  - **Shell:** Codex ran 63 shell commands, at least one in every attempt. These included statement arithmetic in Python and file searches of its empty working directory.
  - **The eval's answers:** no attempt fetched or read `evals/`, though nothing stopped it. `journeys.json` holds the expected facts.
  - **Local disk:** in the hand-run sessions below, the read-only sandbox read the playbook straight from the local checkout and listed the home directory.
  - **Effect on the comparison:** Claude Code may call only the eval server's tools, so Codex's effort is not directly comparable.
  - Filed as [w5/963](../../../../../.pm/w5/963.md).
- **Drift check scope:** the drift line compares only prompts. That is how the undeployed `d812112f6` went unflagged. Filed as [w5/964](../../../../../.pm/w5/964.md).

## `categorize-imports` on staged bank data (by hand)

This check ran on the account owner's QA ledger, which has one linked bank (production Plaid) and three staged transactions.

- **Credential:** a one-day key with `ledger.read` and `ledger.write`, but not `ledger.admin`, pinned to that ledger and revoked afterwards.
- **Prompt:** Codex received the deployed prompt from `prompts/get`, which matches the working tree.
- **Client flags:** the harness's Codex flags, plus one deviation: `discardStagedBankTransactions` was removed from Codex's tool list (`mcp_servers.beancount.disabled_tools`), so a real discard could not happen.
- **Evidence handling:** the ledger and staging were read back over GraphQL after every turn. Transcripts stay local because they hold real bank data.

Results:

- **Discovery:** listing banks was refused for lack of `ledger.admin`. Codex said so, skipped the sync, and worked from what was staged.
- **Suggestions:**
  - For two rows, Codex reused the payee's earlier booking with medium confidence, an unrelated card liability. It flagged the mismatch and asked for confirmation. On 2026-10-21, Claude Code declined the same prior as the wrong card.
  - It left the third row unassigned.
  - It invented no account and used no `Expenses:Uncategorized`. It set aside the server's suggestions as unsupported by the ledger's history.
- **Dedup:** it found no postings to the source account at the same amount within three days, and said so.
- **Declined:** a "No" left the ledger's latest commit, its file, and all three staged rows unchanged.
- **Confirmed one row:**
  - The user corrected the target to a new income account and asked Codex to open it.
  - Codex wrote the `open` directive, then ran a dry run.
  - The first dry run passed the staged row's `id` and got "Some transactions not found in database".
  - The retry passed the `transactionId`. The dry run showed one entry with no new errors, and the real import followed.
  - Two commits resulted, the `open` directive and the transaction, with the expected postings and 0 errors. That row left staging, and two stayed.
  - Codex did not show the dry run to the user before the real call, because the user's "yes" came first. The 2026-10-21 Claude Code session did the same.
- **Repeat run:**
  - Codex proposed only the two rows still staged; the imported row was not proposed again.
  - The ledger kept exactly one such entry.
  - A "No" afterwards changed nothing.
- **Discard:** not exercised.
- **The wrong `id` on the first try** is the gap `d812112f6` repairs, and that change is not deployed (see [Conditions](#conditions)). This is the w5/m5 blocker that remains.

## Not measured

- **Codex isolated like Claude Code,** with the account's connectors and the shell turned off ([w5/963](../../../../../.pm/w5/963.md)).
- **Codex's model, turns, and cost,** which the client does not report.
- **A real discard,** which is destructive on real staged rows.
- **A close on a ledger that starts red:** the harness runs one fixture per suite.
- **Variance** beyond three attempts per journey.
