# w2 · m47 — Turn PDF statements and receipt photos into checked entries with documents attached

**Worker:** worker2 **Goal:** a user whose bank offers only PDF statements, or who has a photo or PDF of a receipt, gets the same reviewed, deduplicated entries a CSV export produces, with the source file attached to the ledger. Extracted rows never count as imported until a `balance` assertion ties them to the statement's closing balance. **Status:** todo

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | Decide where a PDF statement imports, how its rows are identified, and how they dedup against a later CSV | 45m | w2/079 |
| t002 | Import a PDF statement as checked entries, with the statement attached | 75m | t001 |
| t003 | Turn a receipt image or PDF into a proposed entry, with the receipt attached | 45m | t001, w2/m40/t010 |
| t004 | Write evals with synthetic PDF statements and receipts | 60m | t002, t003 |
| t005 | Run the evals and the routing set on Claude Code and Codex | 45m | t004 |
| t006 | Adoption surface | 30m | t005 |
| t007 | Simplify | 15m | t006 |
| t008 | Test coverage | 45m | t006, t007 |
| t009 | Closeout | 15m | t008 |

## Definition of done

- A PDF statement imports through the skill that t001 chose. The skill proposes entries only when opening balance + extracted movements = closing balance. It reports success only after a `balance` assertion dated the day after the statement period passes `bea check`. A statement that does not tie stops before any write, and the skill names the gap.
- Every written row carries an `import-id` in the form t001 adds to `beancount-import/references/dedup.md`. Re-importing the same PDF adds zero entries. A later CSV export covering the same period shows every overlapping row as a suspected duplicate instead of writing it again.
- A receipt image or PDF becomes a proposed `beancount-add` entry. After a yes, the transaction and its `document` directive share a link, and the file sits where the ledger keeps documents. `bea check` passes, and it fails when the file is missing.
- An instruction embedded in a statement or receipt is recorded or flagged, and never followed ([079](../done/079.md)'s rule).
- The routing set includes PDF-statement and receipt-file prompts, and they route correctly on both clients. The new evals pass on Claude Code and Codex, recorded with versions and dates.

## Source + Goal linkage

- **Source:** `/pm-brainstorm` 2026-10-18, item 7, from online research into published Beancount skills and user needs. Evidence: a user who has Claude [read a PDF when the PDF-to-beancount script breaks](https://alexcwatt.com/beancount/); [Beanhand](https://github.com/Rudd-O/beanhand) (receipts to transactions, receipts linked to entries); Fava's open request for [document upload from the transaction form](https://github.com/beancount/fava/issues/566); receipt and PDF stages in [cfo-stack](https://github.com/MikeChongCan/cfo-stack) and [auto-bean](https://github.com/SamArgt/auto-bean).
- **Goal linkage:** **A1 — Agent-native accounting:** an agent records what a statement or receipt shows, with the suite's proposal, dedup, and check rails, instead of the user retyping it. **A2 — Frictionless onboarding:** a newcomer whose bank has no CSV or OFX export can still start a ledger from the PDFs they already have.
- **Expected outcome:** an import or receipt request that names a PDF or an image produces entries tied out by a passing balance assertion, with the file linked from the ledger. Signals: routing-set recall for the new prompts, and invocations of `beancount-import` and `beancount-add` with file inputs.
- **Why now:** `beancount-reconcile` already reads PDF statements and writes missing transactions with generated `import-id`s. Those ids hash the PDF's wording, and `dedup.md`'s fuzzy layer only looks at entries without an `import-id`. So a later CSV of the same month can likely double-book every row, and t001 confirms or rules out this inference. Defining PDF row identity now fixes that path, and it gives the new import path a sound base. The milestone depends on [079](../done/079.md), because statement and receipt text are an injection surface, and on [m40](../blocked/m40/README.md), which ships `beancount-add`. Adoption surface is included because two customer skills gain a new input type.

## Out of scope

- OCR services, cloud extraction, or a new parsing dependency. The agent reads the file with its own client. When it cannot, the skill asks for the text or a CSV.
- Downloading statements by driving the user's logged-in browser, which was rejected in the brainstorm because it hands an agent a live banking session.
- The hosted `parseReceipt` MCP flow and hosted ledgers.
- Brokerage statements with holdings and lots (w2/m45), and statements that cover several accounts at once.
- Changing `bea import`'s duplicate detector. If t001 finds the CLI must change, file that as a follow-up note.
