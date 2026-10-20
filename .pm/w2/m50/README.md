# w2 · m50 — Import investment activity in bulk, with lots intact

**Worker:** worker2 **Goal:** a user with a year of broker or exchange activity — or an existing portfolio to onboard — gets those events into the ledger as correct lots through one reviewed batch proposal, instead of dictating trades one at a time. **Status:** todo (t001–t002 done)

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| [t001](./done/t001.md) | Let beancount-trade propose many described events in one batch — **DONE** | 60m | w2/m45/t002 |
| [t002](./done/t002.md) | Import a broker activity export as lots — **DONE** | 90m | t001 |
| t003 | Import exchange activity and opening lots from a cost-basis export | 75m | t001 |
| t004 | Write evals, fixtures, and routing entries for bulk intake | 60m | t001, t002, t003 |
| t005 | Run the evals and routing set on both clients | 45m | t004 |
| t006 | Adoption surface | 30m | t005 |
| t007 | Simplify | 15m | t006 |
| t008 | Test coverage | 45m | t006, t007 |
| t009 | Closeout | 15m | t008 |

## Definition of done

- A batch of described investment events is proposed once, confirmed once, and written check-gated, with lot ambiguity resolved per event and partial failures reported event-by-event.
- One broker activity format and one exchange activity format import as lots with `import-id` dedup (re-import is a no-op); a sell against an unheld lot stops before any write.
- An opening-lots import seeds existing positions at true cost/date, tied to the export's totals. Evals pass on both clients; routing keeps bank imports, single trades, and bulk intake apart.

## Source + Goal linkage

- **Source:** user walkthrough as a personal investor (real estate, crypto, stocks, daily spending), 2026-10-19.
- **Goal linkage:** **A1 — Agent-native accounting:** per-event dictation caps adoption at toy portfolios; bulk intake is what makes an agent-maintained investment ledger realistic. **A2** for the opening-lots on-ramp.
- **Expected outcome:** a user can onboard an existing portfolio and keep it current from exports, not dictation. Signals: eval pass on both clients, first-year journey rehearsal (m53) using bulk intake.
- **Why now:** m45 proved single-event lot correctness and shipped the batch write recipe's sibling in add; volume is the next wall the walkthrough hits.
