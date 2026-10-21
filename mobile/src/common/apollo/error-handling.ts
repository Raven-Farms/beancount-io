import { router } from "expo-router";
import { sessionVar } from "@/common/vars";
import { oauthTokenManager } from "@/common/oauth/oauth-token-manager";
import { createAuthErrorLink } from "@/common/apollo/auth-error-link";
import { clearGuestVisit } from "@/common/guest/guest-state";
import { invalidateAuthorization } from "@/common/oauth/authorization-context";

let teardownInFlight: Promise<void> | null = null;

function teardownAndRoute(): Promise<void> {
  clearGuestVisit();
  invalidateAuthorization();
  if (!teardownInFlight) {
    // The same cleanup as Log out: a revoked session must not leave its
    // Create Ledger draft, Recent accounts or merchant overrides for the next
    // account on this device (w21/071). Imported lazily because it reaches the
    // Apollo client, which imports this link.
    teardownInFlight = import("@/common/server-url-actions")
      .then(({ clearServerScopedState }) => clearServerScopedState())
      .finally(() => {
        router.replace("/auth/welcome");
        teardownInFlight = null;
      });
  }
  return teardownInFlight;
}

export const onErrorLink = createAuthErrorLink({
  getSession: sessionVar,
  refresh: () => oauthTokenManager.getAccessToken(true),
  teardown: teardownAndRoute,
  onTerminalRefreshFailure: () => router.replace("/auth/welcome"),
});
