import type { OAuthSession, Session } from "@/common/oauth/session-record";

export type LogoutDependencies = {
  cancelRefreshes: () => Promise<void>;
  revokeOAuth: (session: OAuthSession) => Promise<void>;
  revokeLegacy: (authToken: string) => Promise<void>;
  clearLocalState: () => Promise<void>;
  /** Makes the next sign-in ask which account to use (w21/153). */
  markSignedOut: () => Promise<void>;
};

/** Remote revocation is best effort; local account isolation always completes. */
export async function performLogout(
  session: Session,
  dependencies: LogoutDependencies,
): Promise<void> {
  await dependencies.cancelRefreshes();
  try {
    if (session.kind === "oauth") {
      await dependencies.revokeOAuth(session);
    } else {
      await dependencies.revokeLegacy(session.authToken);
    }
  } catch {
    // Offline sign-out still removes every local credential and cached account.
  }

  await dependencies.clearLocalState();
  // After the wipe, so it survives it. Best effort: sign-out itself is done.
  await dependencies.markSignedOut().catch(() => undefined);
}
