import { useSyncExternalStore } from "react";
import { useRouterState } from "@tanstack/react-router";
import { getSafeReturnPath } from "@/common/lib/auth/auth";

/**
 * The current location as a safe relative return path: `next` for
 * `/auth/login`, or `return` for a Billing deep link.
 *
 * Guest actions (star, follow) send the visitor to login themselves rather than
 * through `requireAuth`, so they have to supply the return destination the same
 * way the route guard does — path + search + hash — or login falls back to the
 * default ledger and the visitor never gets back to the page they acted on.
 *
 * The fragment never reaches the server, so until hydration the path leaves
 * it out on both sides; the hydrated render then adds it as an ordinary
 * update. Otherwise the link's server href survived hydration unpatched and
 * a new-tab open lost the fragment that a click kept (w4/244).
 */
const noSubscription = () => () => {};

export function useSafeReturnPath(): string | undefined {
  // False on the server and the hydration render, as TanStack's useHydrated.
  const hydrated = useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );
  return useRouterState({
    select: (state) =>
      getSafeReturnPath(
        hydrated
          ? state.location
          : { ...state.location, href: state.location.href.split("#")[0] },
      ),
  });
}
