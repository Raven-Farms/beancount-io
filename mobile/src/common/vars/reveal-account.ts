import { makeVar } from "@apollo/client";

/** An account just opened, and the ledger it was opened in. */
export type AccountReveal = { ledgerId: string; account: string };

/**
 * An account just opened, for the Accounts table to expand its ancestors
 * and scroll to. Opened under a collapsed parent it was otherwise invisible
 * after Done, as if nothing had happened (w21/175). The table clears it once
 * the row is on screen, or when it belongs to another ledger than the one
 * shown, so it can never act on a different ledger's tree (w21/363).
 */
export const revealAccountVar = makeVar<AccountReveal | null>(null);
