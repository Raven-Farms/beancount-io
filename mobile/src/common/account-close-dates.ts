/**
 * Which accounts a new posting may use on a given date (w21/045).
 *
 * The posting pickers listed every declared account, closed ones included, so
 * a paid-off card could be picked and the save refused only at Done: "Posting
 * to inactive account … (closed on …)". An account closed on or after the
 * entry's date still takes it — Beancount sorts a `close` after same-day
 * transactions, which rustledger confirms — so a back-dated entry can use an
 * account that was open that day.
 *
 * Free of `@/` imports so the jest-lite runner can require it.
 */

/** Close date per account, from `getLedgerAccountDirectives`. */
export type CloseDates = ReadonlyMap<string, string>;

export function closeDatesOf(
  directives:
    readonly { account: string; closedAt?: string | null }[] | null | undefined,
): CloseDates {
  const dates = new Map<string, string>();
  for (const { account, closedAt } of directives ?? []) {
    if (closedAt) dates.set(account, closedAt.slice(0, 10));
  }
  return dates;
}

/** Whether `account` is still open on `entryDate` (YYYY-MM-DD). */
export function isOpenOn(
  account: string,
  entryDate: string,
  closeDates: CloseDates,
): boolean {
  const closedAt = closeDates.get(account);
  return closedAt === undefined || entryDate <= closedAt;
}

/** The accounts a posting dated `entryDate` can use, in their order. */
export function openOn(
  accounts: readonly string[],
  entryDate: string,
  closeDates: CloseDates,
): string[] {
  return accounts.filter((account) => isOpenOn(account, entryDate, closeDates));
}

/**
 * The accounts the Accounts tree lists even at zero: every opened account but
 * those closed on or before `today`. A closed, emptied account kept showing as
 * a live "$0.00" row (w21/099). One closed with a balance left still lists,
 * through the balance itself: that is a ledger problem worth seeing.
 */
export function listedAccountsAsOf(
  accounts: readonly string[],
  today: string,
  closeDates: CloseDates,
): string[] {
  return accounts.filter((account) => {
    const closedAt = closeDates.get(account);
    return closedAt === undefined || closedAt > today;
  });
}
