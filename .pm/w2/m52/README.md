# w2 · m52 — Record crypto-native events: swaps, staking, and network fees

**Worker:** worker2 **Goal:** a crypto holder records a coin-to-coin swap, staking or airdrop income, and a wallet transfer that pays its network fee in-kind — each with lots and booking-produced gains intact. **Status:** todo

## Tasks (in order)

| id   | title | est | depends_on |
| ---- | ----- | --- | ---------- |
| t001 | Record a crypto-to-crypto swap as a priced sell and buy pair | 45m | w2/m45/t002 |
| t002 | Record staking rewards and airdrops as income at fair value | 45m | t001 |
| t003 | Carry an in-kind network fee on own-wallet transfers | 45m | t001 |
| t004 | Write evals, routing entries, and run them on both clients | 60m | t001, t002, t003 |
| t005 | Adoption surface | 30m | t004 |
| t006 | Simplify | 15m | t005 |
| t007 | Test coverage | 45m | t005, t006 |
| t008 | Closeout | 15m | t007 |

## Definition of done

- A swap disposes the named lot at a user-stated value with a booking-produced gain and opens the received lot at that value; no stated value, no entry.
- Staking/airdrop receipts book as dated lots against named income at stated fair values; own-wallet transfers can burn an in-kind fee from the same lot with units reconciling exactly.
- Evals pass on both clients; cash buys, exchange files, and price questions keep routing to their existing owners.

## Source + Goal linkage

- **Source:** user walkthrough as a personal investor (real estate, crypto, stocks, daily spending), 2026-10-19.
- **Goal linkage:** **A1 — Agent-native accounting:** m45 made crypto follow stock rules; these are the events stocks don't have, and they are most of an active holder's year.
- **Expected outcome:** crypto holders stop hand-editing entries for swaps, rewards, and fees. Signals: eval pass on both clients, trade-skill invocations on crypto prompts.
- **Why now:** m45/t002's procedures and eval 7's transfer fixture are the direct base; the gap list came from walking them as a holder.
