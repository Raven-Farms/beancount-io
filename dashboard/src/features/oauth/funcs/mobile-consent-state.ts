import type { MobileConsentSearch } from "./mobile-consent-search";

export type MobileOAuthConsentState =
  | { step: "login" | "forgot_password" | "register" }
  | { step: "otp"; sessionId: string; email: string }
  | {
      step: "choose_account";
      email: string;
      /** What the other button offers: a new account, or signing in anew. */
      alternative: "register" | "login";
    }
  | { step: "approve"; email?: string };

export type MobileOAuthConsentAction =
  | { type: "show_login" }
  | { type: "show_forgot_password" }
  | { type: "show_register" }
  | { type: "registration_submitted"; sessionId: string; email: string }
  | { type: "authenticated"; email?: string };

export type MobileOAuthScreenHint = MobileConsentSearch["screen_hint"];

/**
 * The hints only ever add a step in the user's favour. Sign Up: a signed-out
 * browser opens on registration instead of login, and a signed-in one is asked
 * which account to use instead of being approved straight into the existing
 * one — the silent path that made a "Sign Up" tap look like a broken sign-up.
 * After the app signed out (`select_account`), a still-signed-in browser asks
 * the same instead of a one-tap Approve for the previous user (w21/153).
 */
export function initialMobileOAuthConsentState({
  userProfile,
  screenHint,
}: {
  userProfile?: { email: string } | null;
  screenHint: MobileOAuthScreenHint;
}): MobileOAuthConsentState {
  if (userProfile) {
    if (screenHint === "signup") {
      return {
        step: "choose_account",
        email: userProfile.email,
        alternative: "register",
      };
    }
    if (screenHint === "select_account") {
      return {
        step: "choose_account",
        email: userProfile.email,
        alternative: "login",
      };
    }
    return { step: "approve", email: userProfile.email };
  }
  return { step: screenHint === "signup" ? "register" : "login" };
}

export function mobileOAuthConsentReducer(
  _state: MobileOAuthConsentState,
  action: MobileOAuthConsentAction,
): MobileOAuthConsentState {
  switch (action.type) {
    case "show_login":
      return { step: "login" };
    case "show_forgot_password":
      return { step: "forgot_password" };
    case "show_register":
      return { step: "register" };
    case "registration_submitted":
      return {
        step: "otp",
        sessionId: action.sessionId,
        email: action.email,
      };
    case "authenticated":
      return { step: "approve", email: action.email };
  }
}
