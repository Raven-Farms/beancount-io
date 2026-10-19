/** Stripe amounts are in the currency's minor unit; this is the major unit. */
export function majorUnits(amount: number, currency: string): number {
  const digits =
    new Intl.NumberFormat("en", {
      style: "currency",
      currency,
    }).resolvedOptions().maximumFractionDigits ?? 2;
  return amount / 10 ** digits;
}
