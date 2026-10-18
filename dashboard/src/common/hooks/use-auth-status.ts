import { useRootContext } from "@/common/hooks/use-root-context";
import type { AuthStatus } from "@/common/server-fn/user";

/**
 * The identity probe's three states. Contexts that only carry `userProfile`
 * (older call sites, test routers) derive the two definitive states from it;
 * only the root beforeLoad can produce "unavailable" (w3/646).
 */
export function useAuthStatus(): AuthStatus {
  const { userProfile, authStatus } = useRootContext();
  return authStatus ?? (userProfile != null ? "signed-in" : "signed-out");
}
