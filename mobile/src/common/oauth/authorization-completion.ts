import { persistSession } from "../vars/session";
import { clearAccountChoiceNeeded } from "./account-choice";
import { createAuthorizationCompleter } from "./authorization-completer";
import { finalizeOAuthSignIn } from "./oauth-sign-in-finalizer";
import { createOAuthSessionFromCode } from "./code-exchange";
import { authorizationGeneration } from "./authorization-context";
import { getServerUrl } from "../vars/server-url";
import {
  clearPendingAuthorization,
  loadPendingAuthorization,
} from "./pending-authorization-storage";

export const completeOAuthAuthorization = createAuthorizationCompleter({
  contextVersion: authorizationGeneration,
  canComplete: (pending) => pending.serverUrl === getServerUrl(),
  loadPending: loadPendingAuthorization,
  clearPending: clearPendingAuthorization,
  exchange: createOAuthSessionFromCode,
  // A completed sign-in is the account choice the sign-out asked for.
  persist: async (session, isCurrent) => {
    await persistSession(session, isCurrent);
    if (isCurrent()) await clearAccountChoiceNeeded().catch(() => undefined);
  },
  afterPersist: (_session, pending) => finalizeOAuthSignIn(pending.state),
});
