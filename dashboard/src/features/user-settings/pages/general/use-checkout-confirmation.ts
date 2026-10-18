import { useEffect, useRef, useState } from "react";

/** How long to wait for the Stripe webhook before saying so. */
export const CONFIRMATION_TIMEOUT_MS = 20_000;
const POLL_INTERVAL_MS = 2_000;

export type ConfirmationState = "confirming" | "done" | "pending";

/**
 * Poll subscription status after Checkout until the webhook has recorded the
 * subscription, or until the timeout. Nothing here treats a slow webhook as an
 * error: the customer has paid.
 */
export function useCheckoutConfirmation(
  enabled: boolean,
  recorded: boolean,
  refetch: () => unknown,
): ConfirmationState {
  const [timedOut, setTimedOut] = useState(false);
  const refetchRef = useRef(refetch);
  useEffect(() => {
    refetchRef.current = refetch;
  });

  useEffect(() => {
    if (!enabled || recorded) return;
    const poll = setInterval(() => void refetchRef.current(), POLL_INTERVAL_MS);
    const stop = setTimeout(() => setTimedOut(true), CONFIRMATION_TIMEOUT_MS);
    return () => {
      clearInterval(poll);
      clearTimeout(stop);
    };
  }, [enabled, recorded]);

  if (recorded) return "done";
  return timedOut ? "pending" : "confirming";
}
