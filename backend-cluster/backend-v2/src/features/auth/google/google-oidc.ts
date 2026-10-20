import { createHash, randomBytes } from "node:crypto";
import { createRemoteJWKSet, jwtVerify, type JWTVerifyGetKey } from "jose";
import type { GoogleAuthConfig } from "@/config/config";

/**
 * Sign in with Google as an OpenID Connect relying party (authorization code
 * flow with PKCE and nonce). Everything Google-specific lives here; the
 * routes only move values between the browser, Redis and this module.
 */

const AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth";
const TOKEN_URL = "https://oauth2.googleapis.com/token";
const JWKS_URL = new URL("https://www.googleapis.com/oauth2/v3/certs");
const ISSUERS = ["https://accounts.google.com", "accounts.google.com"];
const TOKEN_TIMEOUT_MS = 10_000;

/** A Google account Google has vouched for, after every check below. */
export interface VerifiedGoogleIdentity {
  /** Google's stable account ID (logged for audit; accounts link by email). */
  sub: string;
  /** Lowercased, verified, and authoritative per Google's guidance. */
  email: string;
  /** Workspace domain (`hd`), or null for a consumer gmail.com account. */
  hostedDomain: string | null;
  givenName: string | null;
  familyName: string | null;
}

/** Why a sign-in was refused; mapped to a stable `reason` for the dashboard. */
export class GoogleSignInError extends Error {
  constructor(
    readonly reason: "google_failed" | "google_unverified" | "google_domain",
    detail: string,
  ) {
    super(detail);
    this.name = "GoogleSignInError";
  }
}

const base64url = (bytes: Buffer): string => bytes.toString("base64url");

/** Fresh per-ceremony secrets: state, nonce and the PKCE verifier. */
export function newCeremonySecrets(): {
  state: string;
  nonce: string;
  codeVerifier: string;
} {
  return {
    state: base64url(randomBytes(32)),
    nonce: base64url(randomBytes(32)),
    codeVerifier: base64url(randomBytes(32)),
  };
}

export function authorizationUrl(
  config: GoogleAuthConfig,
  redirectUri: string,
  secrets: { state: string; nonce: string; codeVerifier: string },
): string {
  const url = new URL(AUTHORIZE_URL);
  url.search = new URLSearchParams({
    client_id: config.clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    scope: "openid email profile",
    state: secrets.state,
    nonce: secrets.nonce,
    code_challenge: base64url(
      createHash("sha256").update(secrets.codeVerifier).digest(),
    ),
    code_challenge_method: "S256",
    prompt: "select_account",
    // A hint for Google's account chooser only; enforcement is on the token.
    ...(config.hostedDomains.size === 1
      ? { hd: [...config.hostedDomains][0] }
      : {}),
  }).toString();
  return url.toString();
}

export interface GoogleOidcDeps {
  fetch: typeof fetch;
  keys: JWTVerifyGetKey;
}

let defaultKeys: JWTVerifyGetKey | undefined;
export function defaultGoogleOidcDeps(): GoogleOidcDeps {
  // One JWKS cache per process; jose refreshes on unknown `kid` (key rotation).
  defaultKeys ??= createRemoteJWKSet(JWKS_URL);
  return { fetch: globalThis.fetch, keys: defaultKeys };
}

/** Exchange the authorization code and verify the ID token it returns. */
export async function completeGoogleSignIn(
  config: GoogleAuthConfig,
  redirectUri: string,
  input: { code: string; codeVerifier: string; nonce: string },
  deps: GoogleOidcDeps,
): Promise<VerifiedGoogleIdentity> {
  let response: Response;
  try {
    response = await deps.fetch(TOKEN_URL, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        code: input.code,
        code_verifier: input.codeVerifier,
        redirect_uri: redirectUri,
        client_id: config.clientId,
        client_secret: config.clientSecret,
      }),
      signal: AbortSignal.timeout(TOKEN_TIMEOUT_MS),
    });
  } catch {
    throw new GoogleSignInError("google_failed", "token endpoint unreachable");
  }
  if (!response.ok) {
    // Never echo Google's body: it can describe the request.
    throw new GoogleSignInError(
      "google_failed",
      `token endpoint returned ${response.status}`,
    );
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new GoogleSignInError("google_failed", "token response is not JSON");
  }
  const idToken = (body as { id_token?: unknown } | null)?.id_token;
  if (typeof idToken !== "string" || !idToken) {
    throw new GoogleSignInError("google_failed", "no id_token in response");
  }
  return verifyGoogleIdToken(config, idToken, input.nonce, deps.keys);
}

const nonEmptyString = (v: unknown): v is string =>
  typeof v === "string" && v.length > 0;

export async function verifyGoogleIdToken(
  config: GoogleAuthConfig,
  idToken: string,
  expectedNonce: string,
  keys: JWTVerifyGetKey,
): Promise<VerifiedGoogleIdentity> {
  let payload: Record<string, unknown>;
  try {
    ({ payload } = await jwtVerify(idToken, keys, {
      issuer: ISSUERS,
      audience: config.clientId,
      algorithms: ["RS256"],
      requiredClaims: ["iss", "aud", "sub", "exp", "iat", "nonce", "email"],
      clockTolerance: 60,
    }));
  } catch (error) {
    // jose messages can quote claims; keep only the error class.
    throw new GoogleSignInError(
      "google_failed",
      `id_token rejected (${error instanceof Error ? error.name : "unknown"})`,
    );
  }

  // Single audience only: a token minted for several clients is not ours alone.
  const aud = payload.aud;
  if (Array.isArray(aud) && (aud.length !== 1 || aud[0] !== config.clientId)) {
    throw new GoogleSignInError(
      "google_failed",
      "id_token has extra audiences",
    );
  }
  if (payload.azp !== undefined && payload.azp !== config.clientId) {
    throw new GoogleSignInError("google_failed", "id_token azp mismatch");
  }
  if (!nonEmptyString(payload.sub)) {
    throw new GoogleSignInError("google_failed", "id_token has no sub");
  }
  if (payload.nonce !== expectedNonce) {
    throw new GoogleSignInError("google_failed", "id_token nonce mismatch");
  }

  const rawEmail = payload.email;
  const email = nonEmptyString(rawEmail) ? rawEmail.trim().toLowerCase() : "";
  const at = email.indexOf("@");
  if (at <= 0 || email.indexOf("@", at + 1) !== -1) {
    throw new GoogleSignInError("google_failed", "id_token email is malformed");
  }
  if (payload.email_verified !== true) {
    throw new GoogleSignInError("google_unverified", "email not verified");
  }

  // Google is authoritative for an address only when it is a Workspace
  // account (`hd`) or a consumer gmail.com account.
  const emailDomain = email.slice(at + 1);
  const hd = nonEmptyString(payload.hd) ? payload.hd.toLowerCase() : null;
  if (hd !== null && hd !== emailDomain) {
    throw new GoogleSignInError("google_domain", "hd does not match email");
  }
  if (hd === null && emailDomain !== "gmail.com") {
    throw new GoogleSignInError("google_unverified", "email not authoritative");
  }
  if (
    config.hostedDomains.size > 0 &&
    (hd === null || !config.hostedDomains.has(hd))
  ) {
    throw new GoogleSignInError("google_domain", "hosted domain not allowed");
  }

  const name = (v: unknown): string | null =>
    nonEmptyString(v) ? v.trim().slice(0, 100) : null;
  return {
    sub: payload.sub,
    email,
    hostedDomain: hd,
    givenName: name(payload.given_name),
    familyName: name(payload.family_name),
  };
}
