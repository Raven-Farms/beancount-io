/** Add Budget's example amount. */
const EXAMPLE_AMOUNT = "500";

/**
 * The Amount field's placeholder. Updating a budget, it is the budget's
 * current amount: a stock "500" beside the prefilled account, interval and
 * currency read as the budget's value (w21/034). The field itself stays
 * empty, so a new amount is still typed. Adding a budget keeps the example.
 */
export function budgetAmountPlaceholder(
  isUpdate: boolean,
  currentAmount: string | undefined,
): string {
  const number = currentAmount?.trim().split(/\s+/)[0] ?? "";
  return isUpdate && /^-?\d+(\.\d+)?$/.test(number) ? number : EXAMPLE_AMOUNT;
}
