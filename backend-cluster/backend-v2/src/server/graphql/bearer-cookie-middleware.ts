import type { Middleware } from "koa";
import type { AppConfig } from "@/config/config";
import { setAuthCookie, getAuthCookieFromCtx } from "@/shared/cookie-utils";
import { verifyJwt } from "@/features/auth/utils/jwt-crypto-utils";

/**
 * A GraphQL caller that authenticates with a valid session bearer token but has
 * no session cookie gets the cookie set, so the browser session continues on
 * cookies. The cookie Domain follows AUTH_COOKIE_DOMAIN (config.jwt.cookieDomain).
 */
export function bearerCookieMiddleware(
  config: Pick<AppConfig, "env" | "jwt">,
): Middleware {
  return async (ctx, next) => {
    const authHeader = ctx.headers.authorization;
    const existingCookie = getAuthCookieFromCtx(ctx);

    if (authHeader && !existingCookie) {
      const token = String(authHeader).replace(/^Bearer\s+/, "");
      const decoded = await verifyJwt(token, config.jwt.secret);
      if (decoded) {
        setAuthCookie(
          ctx,
          token,
          new Date(decoded.exp * 1000),
          config.env === "production",
          config.jwt.cookieDomain,
        );
      }
    }

    await next();
  };
}
