import { Context } from "koa";

export const COOKIE_NAME = "authSess:beancount.io";

interface CookieOptions {
  maxAge: number;
  httpOnly: boolean;
  secure: boolean;
  sameSite: "strict" | "lax" | "none";
  path: string;
  domain?: string;
}

export function setAuthCookie(
  ctx: Context,
  token: string,
  expireAt: Date,
  isProduction: boolean,
  // Required (pass config.jwt.cookieDomain) so no caller silently falls back to .beancount.io.
  cookieDomain: string | null | undefined,
): void {
  ctx.cookies.set(
    COOKIE_NAME,
    token,
    getCookieOptions(ctx, expireAt, isProduction, cookieDomain),
  );
}

/**
 * `undefined` keeps the managed default (`.beancount.io` in production);
 * `null` means host-only; a string is used as given. See AUTH_COOKIE_DOMAIN.
 */
export function resolveCookieDomain(
  isProduction: boolean,
  cookieDomain: string | null | undefined,
): string | undefined {
  if (cookieDomain === null) return undefined;
  if (cookieDomain !== undefined) return cookieDomain;
  return isProduction ? ".beancount.io" : undefined;
}

function getCookieOptions(
  context: Context,
  expireAt: Date,
  isProduction: boolean,
  cookieDomain: string | null | undefined,
): CookieOptions {
  return {
    // Mirrors the JWT's own expiry so the cookie never outlives the token it carries.
    maxAge: Math.max(0, expireAt.getTime() - Date.now()),
    httpOnly: true, // Prevent JavaScript access
    secure: context.URL.protocol === "https:", // HTTPS only in production
    sameSite: "lax", // CSRF protection
    path: "/",
    // Managed production shares the cookie across *.beancount.io (api.v3,
    // dashboard.v3, ...); self-hosts override it with AUTH_COOKIE_DOMAIN.
    domain: resolveCookieDomain(isProduction, cookieDomain),
  };
}

// Duck-typed on the one call made: Koa and @koa/router contexts carry
// structurally identical cookie jars whose fluent `set` return type (`this`)
// defeats nominal assignability between the two type graphs.
// Pass the same isProduction/cookieDomain used to set the cookie: a cookie set
// with a Domain attribute is only deleted by a Set-Cookie with that Domain.
export function clearAuthCookie(
  ctx: {
    cookies: {
      set(
        name: string,
        value: string,
        opts: { maxAge: number; path?: string; domain?: string },
      ): unknown;
    };
  },
  isProduction: boolean,
  cookieDomain: string | null | undefined,
): void {
  const domain = resolveCookieDomain(isProduction, cookieDomain);
  ctx.cookies.set(COOKIE_NAME, "", {
    maxAge: 0,
    path: "/",
    ...(domain ? { domain } : {}),
  });
}

/**
 * Read the auth cookie, tolerating a context that has no cookie jar.
 *
 * Not every caller holds a full Koa context: the shared identity gate
 * (`server/api/identity.ts`) accepts anything header-shaped, and Apollo hands
 * GraphQL a context whose declared type is headers-only. A missing jar means
 * "no cookie was presented", which is a legitimate answer — not a crash.
 */
export function getAuthCookieFromCtx(ctx: Context): string | undefined {
  return ctx.cookies?.get(COOKIE_NAME);
}
