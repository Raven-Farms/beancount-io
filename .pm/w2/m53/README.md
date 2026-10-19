# w2 · m53 — Onboard an investor household, and prove it with a first-year journey

**Worker:** worker2 **Goal:** a new user with brokerage, crypto, and property accounts starts a ledger that already has the right accounts and booking methods, then follows one documented first-year journey — income, investments, a home, year-end gains — across the skills m49-m52 complete. **Status:** todo

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | Add an investor account checklist and booking-method guidance to beancount-init | 60m | — |
| t002 | Write the first-year investor journey guide | 75m | t001, w2/m49/t001, w2/m50/t001, w2/m51/t003, w2/m52/t001 |
| t003 | Rehearse the first-year journey on both clients and write its verifier | 75m | t002 |
| t004 | Adoption surface | 30m | t003 |
| t005 | Simplify | 15m | t004 |
| t006 | Test coverage | 45m | t004, t005 |
| t007 | Closeout | 15m | t006 |

## Definition of done

- A new investor household's init proposes the right investment/property accounts with booking methods explained and confirmed before any `open` is written; the rehearsed ledger passes `bea check` and takes a first trade with no extra opens.
- The first-year guide's every command runs verbatim; a deterministic verifier checks its exact ledger/git effects; both clients complete it in rehearsal with evidence recorded.

## Source + Goal linkage

- **Source:** user walkthrough as a personal investor (real estate, crypto, stocks, daily spending), 2026-10-19.
- **Goal linkage:** **A2 — Frictionless onboarding:** investors are the users most likely to bounce at setup (missing accounts, unexplained booking methods). **A3** for a publishable end-to-end proof that an agent can keep a real household's books.
- **Expected outcome:** an investor goes from zero to a correct, complete household ledger by following one document. Signals: guide completion in rehearsal on both clients, init-skill invocations choosing investment accounts.
- **Why now:** Sequenced last on purpose: it is the integration proof for m49-m52, and each of its stages names the milestone task that makes it possible.
