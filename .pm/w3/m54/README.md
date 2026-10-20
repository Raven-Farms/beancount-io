# w3 · m54 — Ledger creation: staged creation flow on dashboard and mobile

**Worker:** worker3 **Goal:** the m53 setup specification becomes a staged, resumable creation flow on web and native, where accepting every default still reaches a valid private ledger unasked. **Status:** todo

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Build the staged dashboard creation flow | 120m | w3/m53/t005 |
| t002 | Build the same staged flow on mobile | 90m | w3/m53/t005, t001 |
| t003 | Separate the fictional demo from real starters | 45m | t001 |
| t004 | Adoption surface | 30m | t002, t003 |
| t005 | Simplify | 20m | t004 |
| t006 | Test coverage | 45m | t004 |
| t007 | Closeout | 10m | t005, t006 |

## Definition of done

- A customer who accepts every default reaches a valid private ledger without answering a question, on dashboard and on mobile.
- A customer who picks a preset, a non-USD currency, and a `known` opening balance reviews exactly the files and accounts m53's preview promised before confirming.
- Currency suggestion follows ADR021 precedence (explicit selection, native hint, single-currency region, USD); language alone never selects a currency, and a correction survives re-renders, starter switches, validation errors, back navigation, and OTP retries.
- Abandoning the flow mid-way and returning resumes without duplicating the ledger (creation replays on m53's `requestId`).
- The fictional Sample activity is a clearly labelled learning ledger, never mixed into a real starter; the web create button and Starter copy no longer promise what the Starter does not contain.

## Source + Goal linkage

- **Source:** `/pm-brainstorm w3` 2026-10-20 candidate 2, from [PRFAQ001](../../../docs/prfaqs/PRFAQ001-ledger-creation.md) and [ADR021](../../../docs/adrs/ADR021-backend-v2-ledger-creation-experience.md), which record the current one-shot form, the "Save" button, and the stale Starter copy as known defects.
- **Goal linkage:** A2 — Frictionless onboarding.
- **Expected outcome:** first-time users finish creation and record a first transaction instead of stalling on a four-field form that front-loads every decision. Signals: signup-to-first-transaction completion, creation-flow abandonment by stage.
- **Why now:** sequenced directly after m53, whose specification, preview, and idempotent create this flow consumes; building UI first would hard-code a contract that does not exist yet. Adoption surface is included (t004) because both clients' creation journeys change.
