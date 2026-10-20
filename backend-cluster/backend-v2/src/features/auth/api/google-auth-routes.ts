import { timingSafeEqual } from "node:crypto";
import type Router from "@koa/router";
import type { RouterContext } from "@koa/router";
import type { Context } from "koa";
import type { AppConfig } from "@/config/config";
import type { IAuthSessionWorkflow } from "@/features/auth/workflow/auth-session-workflow";
import {
  authorizationUrl,
  completeGoogleSignIn,
  defaultGoogleOidcDeps,
  GoogleSignInError,
  newCeremonySecrets,
  type GoogleOidcDeps,
} from "@/features/auth/google/google-oidc";
import {
  redisGoogleStateStore,
  type GoogleStateStore,
} from "@/features/auth/google/google-state-store";
import { setAuthCookie } from "@/shared/cookie-utils";
import { ForbiddenError } from "@/shared/errors";
import { logger } from "@/shared/logger";
import { getSafeRedirectPath } from "@/shared/safe-redirect-path";

/**
 * Sign in with Google: the browser-facing half of the ceremony.
 *
 *   GET /api-gateway/auth/providers        { google: boolean } for the dashboard
 *   GET /api-gateway/auth/google/start     -> Google (state, nonce, PKCE)
 *   GET /api-gateway/auth/google/callback  -> session cookie, then `next`
 *
 * The redirect URI is DASHBOARD_URL + /api-gateway/auth/google/callback, so the
 * deployment serves /api-gateway/ on the dashboard host and the session
 * cookie lands there (AUTH_COOKIE_DOMAIN must suit that host). Failures return
 * to /auth/login?reason=<code>; details go to the log as categories only.
 */

const GOOGLE_REASONS = [
  "google_unavailable",
  "google_cancelled",
  "google_state",
  "google_failed",
  "google_unverified",
  "google_domain",
  "google_not_allowed",
  "google_blocked",
] as const;
type GoogleReason = (typeof GOOGLE_REASONS)[number];

const STATE_COOKIE = "bcio_google_state";
const CEREMONY_PATH = "/api-gateway/auth/google";
const moduleLogger = logger.child({ module: "google-auth" });

export interface GoogleAuthRouteDeps {
  authSession: Pick<IAuthSessionWorkflow, "signInWithGoogle">;
  config: Pick<AppConfig, "env" | "googleAuth" | "dashboard" | "jwt">;
  stateStore?: GoogleStateStore;
  oidc?: () => GoogleOidcDeps;
}

const single = (v: unknown): string | undefined =>
  typeof v === "string" && v.length > 0 && v.length <= 2048 ? v : undefined;

const sameSecret = (a: string, b: string): boolean => {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
};

export function setGoogleAuthRoutes(
  router: Router,
  deps: GoogleAuthRouteDeps,
): void {
  const { config } = deps;
  const store = deps.stateStore ?? redisGoogleStateStore;
  const oidc = deps.oidc ?? defaultGoogleOidcDeps;
  const dashboard = (path: string) =>
    new URL(path, config.dashboard.url).toString();
  const redirectUri = dashboard(`${CEREMONY_PATH}/callback`);

  const ceremonyHeaders = (ctx: RouterContext) => {
    ctx.set("Cache-Control", "no-store");
    ctx.set("Referrer-Policy", "no-referrer");
  };
  const stateCookie = (ctx: RouterContext, value: string | null) =>
    ctx.cookies.set(STATE_COOKIE, value, {
      httpOnly: true,
      sameSite: "lax",
      secure: ctx.protocol === "https",
      path: CEREMONY_PATH,
      maxAge: value === null ? 0 : 10 * 60 * 1000,
      overwrite: true,
    });
  const backToLogin = (
    ctx: RouterContext,
    reason: GoogleReason,
    next: string,
  ) => {
    moduleLogger.info("Google sign-in did not complete", { reason });
    const url = new URL("/auth/login", config.dashboard.url);
    url.searchParams.set("reason", reason);
    if (next !== "/") url.searchParams.set("next", next);
    ctx.redirect(url.toString());
  };

  router.get("/api-gateway/auth/providers", (ctx) => {
    ctx.set("Cache-Control", "public, max-age=60");
    ctx.body = { google: config.googleAuth !== null };
  });

  router.get(`${CEREMONY_PATH}/start`, async (ctx) => {
    ceremonyHeaders(ctx);
    const next = getSafeRedirectPath(single(ctx.query.next)) ?? "/";
    const google = config.googleAuth;
    if (!google) return backToLogin(ctx, "google_unavailable", next);

    const secrets = newCeremonySecrets();
    try {
      await store.put(secrets.state, {
        nonce: secrets.nonce,
        codeVerifier: secrets.codeVerifier,
        next,
      });
    } catch (error) {
      moduleLogger.error("Google sign-in state not stored", {
        errorType: error instanceof Error ? error.name : "unknown",
      });
      return backToLogin(ctx, "google_failed", next);
    }
    stateCookie(ctx, secrets.state);
    ctx.redirect(authorizationUrl(google, redirectUri, secrets));
  });

  router.get(`${CEREMONY_PATH}/callback`, async (ctx) => {
    ceremonyHeaders(ctx);
    const google = config.googleAuth;
    const cookieState = ctx.cookies.get(STATE_COOKIE);
    stateCookie(ctx, null);
    if (!google) return backToLogin(ctx, "google_unavailable", "/");

    // The state must come back to the browser that started the ceremony
    // before it is spent: a mismatched or missing cookie consumes nothing.
    const state = single(ctx.query.state);
    if (!state || !cookieState || !sameSecret(state, cookieState)) {
      return backToLogin(ctx, "google_state", "/");
    }
    let record;
    try {
      record = await store.consume(state);
    } catch (error) {
      moduleLogger.error("Google sign-in state unavailable", {
        errorType: error instanceof Error ? error.name : "unknown",
      });
      return backToLogin(ctx, "google_failed", "/");
    }
    if (!record) return backToLogin(ctx, "google_state", "/");
    const next = getSafeRedirectPath(record.next) ?? "/";

    if (ctx.query.error !== undefined) {
      return backToLogin(ctx, "google_cancelled", next);
    }
    const code = single(ctx.query.code);
    if (!code) return backToLogin(ctx, "google_failed", next);

    let identity;
    try {
      identity = await completeGoogleSignIn(
        google,
        redirectUri,
        { code, codeVerifier: record.codeVerifier, nonce: record.nonce },
        oidc(),
      );
    } catch (error) {
      if (error instanceof GoogleSignInError) {
        moduleLogger.warn("Google identity refused", {
          reason: error.reason,
          detail: error.message,
        });
        return backToLogin(ctx, error.reason, next);
      }
      moduleLogger.error("Google sign-in failed", {
        errorType: error instanceof Error ? error.name : "unknown",
      });
      return backToLogin(ctx, "google_failed", next);
    }

    let session;
    try {
      session = await deps.authSession.signInWithGoogle(identity, ctx.ip);
    } catch (error) {
      if (error instanceof ForbiddenError) {
        const resource = error.metadata?.resource;
        return backToLogin(
          ctx,
          resource === "user" ? "google_blocked" : "google_not_allowed",
          next,
        );
      }
      moduleLogger.error("Google sign-in could not open a session", {
        errorType: error instanceof Error ? error.name : "unknown",
      });
      return backToLogin(ctx, "google_failed", next);
    }

    moduleLogger.info("Google sign-in", { sub: identity.sub });
    setAuthCookie(
      ctx as unknown as Context,
      session.token,
      session.expireAt,
      config.env === "production",
      config.jwt.cookieDomain,
    );
    ctx.redirect(dashboard(next));
  });
}
