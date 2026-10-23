import * as SecureStore from "expo-secure-store";
import { createPersistentVar } from "@/common/apollo/persistent-var";
import { secureSessionStorage } from "@/common/apollo/secure-session-storage";
import { OAuthAuthorizationError } from "@/common/oauth/authorization-result";
import { markAccountChoiceNeeded } from "@/common/oauth/account-choice";
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
 * without holding up launch; the Keychain copy is gone either way. The next
 * Sign In asks for an account choice.
 */
export async function forgetSessionFromPreviousInstall(): Promise<void> {
  // The system browser's cookies survive an uninstall too, so the consent page
  // would still offer the previous account's one-tap Approve: the next Sign In
  // has to ask for an account choice, as after a sign-out (w21/318). On every
  // fresh install, found session or not: Android's Keystore data does not
  // outlive an uninstall, so the session is gone and the cookies are not
  // (w21/442).
  await markAccountChoiceNeeded().catch(() => undefined);
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
