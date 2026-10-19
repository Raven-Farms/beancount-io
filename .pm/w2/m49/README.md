# w2 · m49 — See what a portfolio holds and what it is worth

**Worker:** worker2 **Goal:** a user who asks "what do I hold, what is it worth, and how is it allocated" gets per-lot holdings at cost and — when prices exist — at market value with unrealized gains, from shown queries; missing prices are named, never silently replaced by cost. **Status:** todo (t001 done)

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| [t001](./done/t001.md) | Add holdings, allocation, and unrealized-gain recipes to beancount-ask — **DONE** | 60m | — |
| t002 | Give price refresh an owner and a documented path | 45m | t001 |
| t003 | Write evals for holdings questions and run them on both clients | 45m | t001, t002 |
| t004 | Adoption surface | 30m | t003 |
| t005 | Simplify | 15m | t004 |
| t006 | Test coverage | 45m | t004, t005 |
| t007 | Closeout | 15m | t006 |

## Definition of done

- "What do I hold and what is it worth" is answered per open lot (units, cost, acquisition date) from shown `bea` queries; market value and unrealized gain appear only where a `price` directive exists, and unpriced commodities are named as gaps.
- Allocation shares sum to the valued total they are computed from, and the cost-basis total ties to the existing book-value net-worth recipe on the same fixture.
- One documented, confirm-gated path refreshes stale prices, and ask's missing-price output names it. The new evals pass on Claude Code and Codex, recorded with versions and dates.

## Source + Goal linkage

- **Source:** user walkthrough as a personal investor (real estate, crypto, stocks, daily spending), 2026-10-19.
- **Goal linkage:** **A1 — Agent-native accounting:** the most common investor question ("what's my portfolio worth") currently has no skill owner; trade covers closed lots, ask covers spending.
- **Expected outcome:** investors can see holdings, allocation, and unrealized gains without leaving the agent workflow, and know exactly which prices are stale. Signals: holdings-question routing recall, eval pass on both clients.
- **Why now:** [m45](../blocked/m45/README.md) shipped correct lots and realized gains; open-lot valuation is the read side it explicitly left uncovered, and it needs no new write path.
