import { makeVar } from "@apollo/client";

/**
 * Why the app signed the user out, when it was not the user's own Log out: a
 * revoked or expired session. Welcome says so once, instead of the stack
 * vanishing without a word under a raw "OAuth grant is no longer valid" alert
 * (w21/119). Cleared when the next sign-in starts.
 */
export type SignOutReason = "sessionEnded";

export const signOutReasonVar = makeVar<SignOutReason | null>(null);
