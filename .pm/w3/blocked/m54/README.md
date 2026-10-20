# w3 · m54 — Ledger creation: staged creation flow on dashboard and mobile

**Worker:** worker3 **Goal:** the m53 setup specification becomes a staged, resumable creation flow on web and native, where accepting every default still reaches a valid private ledger unasked. **Status:** todo (t001–t002, t004–t006 done; t003 blocked — see Blocked)

## Tasks (in order)

| id | title | est | depends_on |
| --- | --- | --- | --- |
| t001 | Build the staged dashboard creation flow — **DONE** | 120m | w3/m53/t005 |
| t002 | Build the same staged flow on mobile — **DONE** | 90m | w3/m53/t005, t001 |
| t003 | Separate the fictional demo from real starters | 45m | t001 |
| t004 | Adoption surface — **DONE** | 30m | t002, t003 |
| t005 | Simplify — **DONE** | 20m | t004 |
| t006 | Test coverage — **DONE** | 45m | t004 |
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

## Blocked

- **t003** — the shipped demo separation (creation choice + in-ledger identity) is done; the remaining list-identification criterion waits on an API-visible demo flag on the ledger directory surfaces. Unblock condition is written in t003.

## Blocked (2026-10-20)

Closeout (t007) cannot run: the milestone's definition of done is not fully met. t003's remaining criterion — a demo ledger identifiable as fictional in ledger lists — waits on an API-visible demo flag on the ledger directory surfaces, and the Starter-copy correction lives in inbox note 648.

**Unblock:** the ledger directory surfaces (REST/GraphQL/MCP in parity) expose a demo flag sourced from the ledger's `bcio_demo` identity or recorded at creation, and w3/648 has shipped. Who can clear it: whoever next extends the ledger directory read in backend-v2 (for the flag) and any worker (for 648).
