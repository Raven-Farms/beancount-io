import * as SecureStore from "expo-secure-store";
import { createPersistentVar } from "@/common/apollo/persistent-var";
import { secureSessionStorage } from "@/common/apollo/secure-session-storage";
import { OAuthAuthorizationError } from "@/common/oauth/authorization-result";
import { revokeOAuthSession } from "@/common/oauth/token-manager";
import {
  deserializeSession,
  type Session,
} from "@/common/oauth/session-record";

export { type Session } from "@/common/oauth/session-record";

export const [sessionVar, loadSession, flushSession] =
  createPersistentVar<Session | null>(
    "session",
    null,
    undefined,
    deserializeSession,
    secureSessionStorage,
  );

/** Persist the newest rotated credential before any waiting caller can use it. */
export async function persistSession(
  session: Session,
  isCurrent = () => true,
): Promise<void> {
  if (!isCurrent())
    throw new OAuthAuthorizationError("authorization_context_changed");
  await secureSessionStorage.setItem("session", JSON.stringify(session));
  if (!isCurrent()) {
    await secureSessionStorage.setItem("session", JSON.stringify(sessionVar()));
    throw new OAuthAuthorizationError("authorization_context_changed");
  }
  sessionVar(session);
  await flushSession();
}

/**
 * Drop a session the Keychain kept from before the app was deleted, before
 * anything restores it (w21/154). The refresh token is revoked best effort,
 * without holding up launch; the Keychain copy is gone either way.
 */
export async function forgetSessionFromPreviousInstall(): Promise<void> {
  const stored = await SecureStore.getItemAsync("session").catch(() => null);
  if (stored === null) return;
  try {
    const session = deserializeSession(stored);
    if (session?.kind === "oauth") {
      void revokeOAuthSession(session).catch(() => undefined);
    }
  } catch {
    // Unreadable: nothing to revoke, and it is deleted below all the same.
  }
  await SecureStore.deleteItemAsync("session");
}
