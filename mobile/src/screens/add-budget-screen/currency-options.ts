/**
 * The currencies Add Budget offers: the ledger's operating currencies first, in
 * its order, then every other commodity it knows (and any typed in), sorted, and
 * USD only when it knows none. The current value is always among them: a budget
 * in a non-operating currency opened the picker on the first option, and Done
 * switched it there without a word (w21/121). Only the operating currencies were
 * offered, so a ledger without `operating_currency` budgeted in a blind USD and
 * read $0 spent against its real spending (w21/395).
 */
export function budgetCurrencyOptions(
  operating: readonly string[],
  current: string,
  all: readonly string[] = [],
  typed: readonly string[] = [],
): string[] {
  const first = [...new Set(operating)];
  const rest = [...new Set([...all, ...typed])]
    .filter((currency) => !first.includes(currency))
    .sort();
  const options = [...first, ...rest];
  const base = options.length > 0 ? options : ["USD"];
  return current && !base.includes(current) ? [...base, current] : base;
}

/**
 * The currency a new budget starts in: the first operating currency, else the
 * first commodity the ledger has, else USD for a ledger that has none yet.
 */
export function defaultBudgetCurrency(
  operating: readonly string[],
  all: readonly string[],
): string {
  return operating[0] ?? all[0] ?? "USD";
}
