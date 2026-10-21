import { getServerUrl } from "../vars/server-url";
import { persistSession, sessionVar } from "../vars/session";
import { signOutReasonVar } from "../vars/sign-out-reason";
import { OAuthTokenManager } from "./token-manager";

export const oauthTokenManager = new OAuthTokenManager({
  getSession: sessionVar,
  getServerUrl,
  persistSession,
  onTerminalFailure: async () => {
    // Not the user's own Log out: Welcome says the session ended (w21/119).
    signOutReasonVar("sessionEnded");
    const { clearServerScopedState } = await import("../server-url-actions");
    await clearServerScopedState({ refreshAlreadyTerminal: true });
  },
});
