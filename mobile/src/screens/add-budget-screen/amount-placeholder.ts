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
  // An income target is stored negative, but the form asks for the positive
  // amount: the placeholder is the magnitude, plain (a grouped one would invite
  // text the amount field refuses) (w21/399).
  return isUpdate && /^-?\d+(\.\d+)?$/.test(number)
    ? number.replace(/^-/, "")
    : EXAMPLE_AMOUNT;
}
