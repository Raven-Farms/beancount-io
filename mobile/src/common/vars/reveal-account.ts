import { makeVar } from "@apollo/client";

/**
 * An account just opened, for the Accounts table to expand its ancestors
 * and scroll to. Opened under a collapsed parent it was otherwise invisible
 * after Done, as if nothing had happened (w21/175). The table clears it once
 * the row is on screen.
 */
export const revealAccountVar = makeVar<string | null>(null);
