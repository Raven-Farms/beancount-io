import type { NativeSignIn } from "./use-native-sign-in";

/**
 * The translation key for a failed sign-in or sign-up. A server problem is named
 * as one, in the same words the Server screen's "Test connection" uses, so a
 * stale custom URL does not read as a wrong password; only a rejection blames
 * the sign-in or sign-up itself. Welcome and the example drawer share it: the
 * drawer said "Could not complete sign-in" for every reason, offline included
 * (w21/634).
 */
export function signInFailureMessageKey(
  failure: NonNullable<NativeSignIn["failure"]>,
): string {
  switch (failure.reason) {
    case "unreachable":
      return "serverConnectionUnreachable";
    case "incompatible":
      return "serverConnectionIncompatible";
    case "timeout":
      return "serverConnectionTimeout";
    case "not_configured":
      return "serverConnectionNotConfigured";
    case "mismatch":
      return "serverConnectionMismatch";
    case "rejected":
      return failure.flow === "sign_up" ? "signUpFailed" : "signInFailed";
  }
}
