import cors from "@koa/cors";
import type { AppConfig } from "@/config/config";

/**
 * CORS origin policy for the API (credentials are allowed, so only trusted
 * origins may be echoed back).
 *
 * Returns the value for Access-Control-Allow-Origin: the request's Origin when
 * it is allowed, "*" for a request without an Origin header (same-origin or
 * non-browser), and "" to omit the header and refuse the cross-origin request.
 *
 * Allowed: beancount.io and its subdomains, localhost/127.0.0.1 on any port
 * (development), and the exact origins in CORS_ALLOWED_ORIGINS (self-hosts).
 */
export function resolveCorsOrigin(
  origin: string,
  extraOrigins: ReadonlySet<string>,
): string {
  if (!origin) {
    return "*";
  }

  let url: URL;
  try {
    url = new URL(origin);
  } catch {
    return "";
  }
  const hostname = url.hostname;

  if (hostname === "beancount.io" || hostname.endsWith(".beancount.io")) {
    return origin;
  }

  // Exact scheme + host + port match against the configured self-host origins.
  if (extraOrigins.has(url.origin)) {
    return origin;
  }

  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return origin;
  }

  return "";
}

/** The API's credentialed CORS middleware, as mounted by start-server. */
export function apiCorsMiddleware(
  config: Pick<AppConfig, "server">,
): ReturnType<typeof cors> {
  return cors({
    origin: (ctx) =>
      resolveCorsOrigin(ctx.get("Origin"), config.server.corsAllowedOrigins),
    credentials: true,
  });
}
