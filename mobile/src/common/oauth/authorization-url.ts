import type { PendingOAuthAuthorization } from "./authorization-result";

/**
 * Build the authorization request from the pending record and nothing else.
 *
 * Every value here is one the callback is later checked against — endpoint,
 * redirect URI, state, resource — so deriving the URL from the same record that
 * validation reads is what keeps the two halves from drifting. Any query the
 * discovered endpoint already carried is dropped rather than merged: a metadata
 * document that smuggles in its own `redirect_uri` or `client_id` must not be
 * able to reach the authorization server through us.
 */
export function buildAuthorizationUrl(
  pending: PendingOAuthAuthorization,
  codeChallenge: string,
  options: { chooseAccount?: boolean } = {},
): string {
  const url = new URL(pending.authorizationEndpoint);
  url.search = new URLSearchParams({
    response_type: "code",
    client_id: pending.clientId,
    redirect_uri: pending.redirectUri,
    scope: pending.scopes.join(" "),
    state: pending.state,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
    resource: pending.resource,
    // OIDC Core §11 makes `offline_access` conditional on an explicit consent
    // prompt, and oidc-provider enforces that by silently dropping the scope
    // otherwise (check_scope.js). Without it the code exchange comes back with
    // no refresh token at all, so the app would sign the user out an hour later
    // with nothing to renew from. Verified against the live authorization
    // endpoint: the same request without `prompt` returns a consent URL whose
    // scope has lost `offline_access`.
    prompt: "consent",
    // The welcome screen has separate Sign In and Sign Up buttons; without
    // this hint the server cannot tell them apart and opens the login form for
    // both. A server that does not know the hint ignores it.
    ...(pending.flow === "sign_up" ? { screen_hint: "signup" } : {}),
    // After a sign-out the browser is still signed in to the previous
    // account; ask for an explicit choice rather than its one-tap Approve
    // (w21/153). Sign Up already asks, through its own hint.
    ...(pending.flow === "sign_in" && options.chooseAccount
      ? { screen_hint: "select_account" }
      : {}),
  }).toString();
  url.hash = "";
  return url.toString();
}
