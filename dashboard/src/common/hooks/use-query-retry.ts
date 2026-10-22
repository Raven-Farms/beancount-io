import { useState } from "react";
import { usePendingAction } from "./use-pending-action";

/**
 * Re-runs a failed query in place, from the Try Again its error view offers
 * (w4/m50). One attempt at a time. Apollo clears `error` while it refetches,
 * so `failure` keeps the error being retried: the error view and its busy
 * Try Again stay mounted, and a rejected retry hands focus back to that
 * button. A rejection is handled here; the query's own `error` reports it.
 *
 * Render the error view on `failure` before any loading state.
 */
export function useQueryRetry<E>(
  error: E | undefined,
  refetch: () => Promise<unknown>,
) {
  const { run, pending } = usePendingAction();
  const [retried, setRetried] = useState(error);
  if (error && error !== retried) setRetried(error);

  return {
    failure: error ?? (pending ? retried : undefined),
    retrying: pending,
    retry: () => {
      void run(() =>
        refetch().then(
          () => true,
          () => false,
        ),
      );
    },
  };
}
