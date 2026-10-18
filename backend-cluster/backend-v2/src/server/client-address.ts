import type Koa from "koa";

/**
 * Make `ctx.ip` the address the nearest of `hops` trusted proxies appended to
 * `X-Forwarded-For`, never an entry the client wrote itself (w0/m7). Koa keeps
 * only the right-most `maxIpsCount` entries; with no proxy trusted it ignores
 * the header and reports the socket address. Every rate limiter keys on this
 * value: REST through `ctx.ip`, GraphQL through `IContext.clientIp`.
 */
export function trustProxyHops(app: Koa, hops: number): void {
  app.proxy = hops > 0;
  app.maxIpsCount = hops;
}
