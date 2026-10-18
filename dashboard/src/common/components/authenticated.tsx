import { useIsAuthenticated } from "@/common/hooks/use-is-authenticated";
import { useAuthStatus } from "@/common/hooks/use-auth-status";

type AuthenticatedProps = {
  children: React.ReactNode;
  fallback?: React.ReactNode;
};

/**
 * Authenticated component with hydration-safe rendering
 * Always renders fallback during SSR and initial client render to prevent hydration mismatches
 * Updates to show authenticated content after hydration if user is authenticated
 */
export const Authenticated = ({ children, fallback }: AuthenticatedProps) => {
  const isAuthenticated = useIsAuthenticated();
  const authStatus = useAuthStatus();
  // While the identity probe is unavailable (an API outage, not a sign-out),
  // show neither side: the fallback is signed-out UI such as "Log In", which
  // would tell a signed-in user their session is gone (w3/646).
  if (authStatus === "unavailable") {
    return null;
  }
  if (!isAuthenticated) {
    return fallback ?? null;
  }
  return children;
};
