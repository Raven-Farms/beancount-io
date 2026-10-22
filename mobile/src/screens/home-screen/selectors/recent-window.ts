/**
 * The window Home's Recent Transactions reads: everything up to and including
 * today. The journal sorts newest first with no cap at today, so entries
 * pre-entered for later (rent for the next five months, forecast or amortize
 * copies) filled all five rows and hid what had actually happened (w21/471). The
 * range needs both ends, so it starts at the earliest date the ledger accepts.
 */
export function recentTransactionsWindow(today: string): string {
  return `0001-01-01 - ${today}`;
}
