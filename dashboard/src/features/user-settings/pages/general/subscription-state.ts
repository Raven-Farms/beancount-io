/**
 * Whether a subscription is set to end: at the period end, or on a date set
 * elsewhere (Stripe's portal sets `cancel_at` without the period-end flag).
 * The Scheduled panel and the billing section must agree on this.
 */
export function isPendingCancellation(subscription: {
  cancelAtPeriodEnd: boolean;
  cancelAt?: string | null;
}): boolean {
  return subscription.cancelAtPeriodEnd || !!subscription.cancelAt;
}
