# w2 · m51 — Track a home, its mortgage, and a rental in the same ledger

**Worker:** worker2 **Goal:** a homeowner records the purchase, each monthly mortgage payment split from statement figures, escrow flows, rental income per property, and eventually the sale — with the property visible in net worth at cost or at a stated price. **Status:** todo

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | Decide the property model and where its procedures live | 45m | — |
| t002 | Record a home purchase and open its mortgage | 60m | t001 |
| t003 | Record the monthly mortgage payment split from statement figures | 60m | t002 |
| t004 | Record rental income per property and a property sale | 60m | t002 |
| t005 | Write evals, fixtures, and routing entries | 60m | t002, t003, t004 |
| t006 | Run the evals and routing set on both clients | 45m | t005 |
| t007 | Adoption surface | 30m | t006 |
| t008 | Simplify | 15m | t007 |
| t009 | Test coverage | 45m | t007, t008 |
| t010 | Closeout | 15m | t009 |

## Definition of done

- A described purchase books property + mortgage + escrow so cash out + loan = price + stated closing costs, check-gated.
- Monthly payments split principal/interest/escrow strictly from statement-printed figures and tie to the printed new balance; a statement without the split produces a question, never a computed entry.
- Rent and expenses report per property; a sale closes property and mortgage with a booking-produced gain. Evals pass on both clients; tenant-rent and statement-line near-misses route to their existing owners.

## Source + Goal linkage

- **Source:** user walkthrough as a personal investor (real estate, crypto, stocks, daily spending), 2026-10-19.
- **Goal linkage:** **A1 — Agent-native accounting:** the largest household asset and liability are invisible to the suite today, so net-worth answers silently omit them.
- **Expected outcome:** homeowners and small landlords can keep property in the same agent-maintained ledger. Signals: eval pass on both clients, net-worth answers that include (or explicitly exclude) property.
- **Why now:** m45's lot/gain mechanics and m48's statement tie-out gates are exactly the machinery a sale and a mortgage split need; only the model and procedures are missing.
