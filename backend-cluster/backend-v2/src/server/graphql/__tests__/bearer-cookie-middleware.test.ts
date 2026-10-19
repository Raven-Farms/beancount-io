import http from "node:http";
import type { AddressInfo } from "node:net";
import Koa from "koa";
import { bearerCookieMiddleware } from "../bearer-cookie-middleware";
import { signJwt } from "@/features/auth/utils/jwt-crypto-utils";

const SECRET = "test-secret";

async function setCookieFor(
  cookieDomain: string | null | undefined,
  bearer?: string,
): Promise<string | null> {
  const app = new Koa();
  app.use(
    bearerCookieMiddleware({
      env: "production",
      jwt: { secret: SECRET, expMins: 60, cookieDomain },
    } as never),
  );
  app.use((ctx) => {
    ctx.body = "ok";
  });
  const server = http.createServer(app.callback());
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const token =
      bearer ??
      (await signJwt(
        {
          jti: "j1",
          sub: "u1",
          iat: Math.floor(Date.now() / 1000),
          exp: Math.floor(Date.now() / 1000) + 600,
        },
        SECRET,
      ));
    const { port } = server.address() as AddressInfo;
    const res = await fetch(`http://127.0.0.1:${port}/api-gateway/`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return res.headers.get("set-cookie");
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

describe("bearerCookieMiddleware cookie Domain (AUTH_COOKIE_DOMAIN)", () => {
  it("keeps the managed .beancount.io Domain when unset", async () => {
    expect(await setCookieFor(undefined)).toMatch(/domain=\.beancount\.io/i);
  });

  it("sets a host-only cookie for host-only", async () => {
    const cookie = await setCookieFor(null);
    expect(cookie).toMatch(/^authSess:beancount\.io=/);
    expect(cookie).not.toMatch(/domain=/i);
  });

  it("uses an explicit Domain", async () => {
    expect(await setCookieFor(".example.com")).toMatch(
      /domain=\.example\.com/i,
    );
  });

  it("sets no cookie for an invalid bearer token", async () => {
    expect(await setCookieFor(null, "not-a-jwt")).toBeNull();
  });
});
