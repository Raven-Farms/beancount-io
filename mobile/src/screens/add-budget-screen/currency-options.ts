/**
 * The currencies Add Budget offers: the ledger's operating currencies (or USD
 * when it declares none), plus the current value when it is none of them. A
 * budget in a non-operating currency opened the picker on the first option,
 * and Done switched it there without a word (w21/121).
 */
export function budgetCurrencyOptions(
  operating: readonly string[],
  current: string,
): string[] {
  const options = operating.length > 0 ? [...operating] : ["USD"];
  return current && !options.includes(current)
    ? [...options, current]
    : options;
}
